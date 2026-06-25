# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PharmacyStockCardWizard(models.TransientModel):
    """Stock Card statement for a period.

    Produces a QuickBooks-style item statement: an Opening Balance line
    (quantity and value as of the day before date_from), every movement
    in the period with a running balance, and a Closing Balance line.
    Each movement line links to its source document.
    """
    _name = 'pharmacy.stock.card.wizard'
    _description = 'Stock Card Statement'

    product_id = fields.Many2one(
        'product.product', string='Product', required=True)
    date_from = fields.Date(
        string='From', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(
        string='To', required=True,
        default=fields.Date.context_today)

    def action_generate(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            from odoo.exceptions import UserError
            raise UserError("'From' date must be on or before 'To' date.")
        Line = self.env['pharmacy.stock.card.line']
        Line.search([('wizard_id', '=', self.id)]).unlink()
        company_id = self.env.company.id

        # --- Opening balance: everything strictly before date_from -------
        # Reconstructed from done stock moves (one side internal = a real
        # in/out of on-hand), valued at the product's cost (standard_price).
        self.env.cr.execute("""
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN dest.usage = 'internal'
                             AND src.usage <> 'internal' THEN sm.product_qty
                        WHEN src.usage = 'internal'
                             AND dest.usage <> 'internal' THEN -sm.product_qty
                        ELSE 0.0
                    END), 0.0) AS qty,
                COALESCE(SUM(
                    CASE
                        WHEN dest.usage = 'internal'
                             AND src.usage <> 'internal' THEN sm.product_qty
                        WHEN src.usage = 'internal'
                             AND dest.usage <> 'internal' THEN -sm.product_qty
                        ELSE 0.0
                    END
                    * COALESCE(
                        (p.standard_price ->> sm.company_id::text)::numeric,
                        0.0)), 0.0) AS value
              FROM stock_move sm
              JOIN product_product p ON sm.product_id = p.id
              JOIN stock_location src ON sm.location_id = src.id
              JOIN stock_location dest ON sm.location_dest_id = dest.id
             WHERE sm.state = 'done'
               AND sm.product_id = %s AND sm.company_id = %s
               AND sm.date::date < %s
               AND (
                   (dest.usage = 'internal' AND src.usage <> 'internal')
                   OR (src.usage = 'internal' AND dest.usage <> 'internal')
               )
        """, (self.product_id.id, company_id, self.date_from))
        open_qty, open_val = self.env.cr.fetchone()

        bal_qty, bal_val = open_qty, open_val
        Line.create({
            'wizard_id': self.id,
            'line_type': 'opening',
            'date': self.date_from,
            'reference': 'Opening Balance',
            'balance_qty': bal_qty,
            'balance_value': bal_val,
        })

        # --- Movements within the period ---------------------------------
        self.env.cr.execute("""
            SELECT sm.id,
                   sm.date,
                   COALESCE(sm.reference, sm.name) AS reference,
                   CASE
                       WHEN dest.usage = 'internal'
                            AND src.usage <> 'internal' THEN sm.product_qty
                       WHEN src.usage = 'internal'
                            AND dest.usage <> 'internal' THEN -sm.product_qty
                       ELSE 0.0
                   END AS quantity,
                   CASE
                       WHEN dest.usage = 'internal'
                            AND src.usage <> 'internal' THEN sm.product_qty
                       WHEN src.usage = 'internal'
                            AND dest.usage <> 'internal' THEN -sm.product_qty
                       ELSE 0.0
                   END * COALESCE(
                       (p.standard_price ->> sm.company_id::text)::numeric,
                       0.0) AS value,
                   COALESCE(
                       (p.standard_price ->> sm.company_id::text)::numeric,
                       0.0) AS unit_cost,
                   sm.id AS stock_move_id,
                   sm.picking_id
              FROM stock_move sm
              JOIN product_product p ON sm.product_id = p.id
              JOIN stock_location src ON sm.location_id = src.id
              JOIN stock_location dest ON sm.location_dest_id = dest.id
             WHERE sm.state = 'done'
               AND sm.product_id = %s AND sm.company_id = %s
               AND sm.date::date >= %s
               AND sm.date::date <= %s
               AND (
                   (dest.usage = 'internal' AND src.usage <> 'internal')
                   OR (src.usage = 'internal' AND dest.usage <> 'internal')
               )
          ORDER BY sm.date, sm.id
        """, (self.product_id.id, company_id, self.date_from, self.date_to))
        rows = self.env.cr.fetchall()

        for (row_id, dt, ref, qty, val, unit_cost,
             move_id, picking_id) in rows:
            qty = qty or 0.0
            val = val or 0.0
            bal_qty += qty
            bal_val += val
            Line.create({
                'wizard_id': self.id,
                'line_type': 'move',
                'date': dt,
                'reference': ref,
                'qty_in': qty if qty > 0 else 0.0,
                'qty_out': -qty if qty < 0 else 0.0,
                'value': val,
                'unit_cost': unit_cost or 0.0,
                'balance_qty': bal_qty,
                'balance_value': bal_val,
                'stock_move_id': move_id,
                'picking_id': picking_id,
            })

        # --- Closing balance ---------------------------------------------
        Line.create({
            'wizard_id': self.id,
            'line_type': 'closing',
            'date': self.date_to,
            'reference': 'Closing Balance',
            'balance_qty': bal_qty,
            'balance_value': bal_val,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': '%s — %s to %s' % (
                self.product_id.display_name,
                self.date_from, self.date_to),
            'res_model': 'pharmacy.stock.card.line',
            'view_mode': 'list',
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
        }


class PharmacyStockCardLine(models.TransientModel):
    """Result rows for the Stock Card statement wizard."""
    _name = 'pharmacy.stock.card.line'
    _description = 'Stock Card Statement Line'
    _order = 'id'

    wizard_id = fields.Many2one('pharmacy.stock.card.wizard',
                                ondelete='cascade', index=True)
    line_type = fields.Selection(
        selection=[('opening', 'Opening'), ('move', 'Movement'),
                   ('closing', 'Closing')],
        string='Type', readonly=True)
    date = fields.Datetime(string='Date', readonly=True)
    reference = fields.Char(string='Reference', readonly=True)
    qty_in = fields.Float(string='Qty In', readonly=True)
    qty_out = fields.Float(string='Qty Out', readonly=True)
    balance_qty = fields.Float(string='Balance Qty', readonly=True)
    value = fields.Float(string='Value Change', readonly=True)
    balance_value = fields.Float(string='Balance Value', readonly=True)
    unit_cost = fields.Float(string='Unit Cost', readonly=True,
                             aggregator='avg')
    stock_move_id = fields.Many2one('stock.move', readonly=True)
    picking_id = fields.Many2one('stock.picking', readonly=True)

    def action_open_source(self):
        """Open the source document behind a movement line."""
        self.ensure_one()
        if self.picking_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': self.picking_id.id,
                'view_mode': 'form', 'target': 'current',
            }
        if self.stock_move_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.move',
                'res_id': self.stock_move_id.id,
                'view_mode': 'form', 'target': 'current',
            }
        return False
