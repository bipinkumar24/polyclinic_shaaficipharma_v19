# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PharmacyStockStatusWizard(models.TransientModel):
    """As-of-date Inventory Stock Status.

    Reconstructs each product's on-hand quantity and value as of any
    chosen date from done stock moves (cumulative up to the date), then
    shows two value columns side by side:
      - Booked value: as-of quantity valued at the product's cost
        (standard_price) at each move.
      - Value at effective cost: as-of quantity x the product's CURRENT
        effective cost (consistent with the other reports).
    """
    _name = 'pharmacy.stock.status.wizard'
    _description = 'Inventory Stock Status (as of date)'

    as_of_date = fields.Date(
        string='As of Date', required=True,
        default=fields.Date.context_today)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        help='Optional: limit to one pharmacy category.')
    hide_zero = fields.Boolean(
        string='Hide Zero Stock', default=True,
        help='Only show products with a non-zero balance on that date.')

    def action_generate(self):
        self.ensure_one()
        Line = self.env['pharmacy.stock.status.line']
        # Clear any previous run for this wizard.
        Line.search([('wizard_id', '=', self.id)]).unlink()

        company_id = self.env.company.id
        # Cumulative quantity and value per product as of the date,
        # reconstructed from done stock moves (one side internal = a real
        # in/out of on-hand). "Booked" value is the as-of quantity valued
        # at the product's cost (standard_price); there is no dependency on
        # stock_account / stock_valuation_layer.
        signed_qty = (
            "CASE "
            "WHEN dest.usage = 'internal' AND src.usage <> 'internal' "
            "THEN sm.product_qty "
            "WHEN src.usage = 'internal' AND dest.usage <> 'internal' "
            "THEN -sm.product_qty ELSE 0.0 END")
        cost = ("COALESCE((p.standard_price ->> sm.company_id::text)"
                "::numeric, 0.0)")
        params = [self.as_of_date, company_id]
        cat_clause = ''
        if self.pharmacy_category_id:
            cat_clause = 'AND t.pharmacy_category_id = %s'
            params.append(self.pharmacy_category_id.id)
        having = ('HAVING SUM(%s) <> 0' % signed_qty) if self.hide_zero else ''

        self.env.cr.execute("""
            SELECT sm.product_id,
                   t.pharmacy_category_id,
                   SUM({signed}) AS qty,
                   SUM({signed} * {cost}) AS value_booked
              FROM stock_move sm
              JOIN product_product p ON sm.product_id = p.id
              JOIN product_template t ON p.product_tmpl_id = t.id
              JOIN stock_location src ON sm.location_id = src.id
              JOIN stock_location dest ON sm.location_dest_id = dest.id
             WHERE sm.state = 'done'
               AND sm.date::date <= %s
               AND sm.company_id = %s
               AND (
                   (dest.usage = 'internal' AND src.usage <> 'internal')
                   OR (src.usage = 'internal' AND dest.usage <> 'internal')
               )
               {cat}
          GROUP BY sm.product_id, t.pharmacy_category_id
               {having}
        """.format(signed=signed_qty, cost=cost,
                   cat=cat_clause, having=having), params)
        rows = self.env.cr.fetchall()
        if not rows:
            return self._show_results()

        product_ids = [r[0] for r in rows]
        # Current moving-average cost for the consistent value column.
        avg_map = self.env['product.effective.cost'].get_moving_avg_cost(
            product_ids, company_id)

        vals = []
        for product_id, cat_id, qty, value_booked in rows:
            qty = qty or 0.0
            value_booked = value_booked or 0.0
            avg_cost = avg_map.get(product_id, 0.0) or 0.0
            vals.append({
                'wizard_id': self.id,
                'as_of_date': self.as_of_date,
                'product_id': product_id,
                'pharmacy_category_id': cat_id,
                'company_id': company_id,
                'qty_on_hand': qty,
                'value_booked': value_booked,
                'avg_unit_cost': (value_booked / qty) if qty else 0.0,
                'value_moving_avg': qty * avg_cost,
                'moving_avg_cost': avg_cost,
            })
        Line.create(vals)
        return self._show_results()

    def _show_results(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Status as of %s' % (self.as_of_date or ''),
            'res_model': 'pharmacy.stock.status.line',
            'view_mode': 'list,pivot',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'search_default_group_category': 1},
            'target': 'current',
        }


class PharmacyStockStatusLine(models.TransientModel):
    """Result rows for the as-of stock status wizard."""
    _name = 'pharmacy.stock.status.line'
    _description = 'Inventory Stock Status Line'
    _order = 'value_booked desc'

    wizard_id = fields.Many2one('pharmacy.stock.status.wizard',
                                ondelete='cascade', index=True)
    as_of_date = fields.Date(string='As of Date', readonly=True)
    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    qty_on_hand = fields.Float(string='Qty On Hand', readonly=True)
    avg_unit_cost = fields.Float(string='Booked Unit Cost', readonly=True,
                                 aggregator='avg')
    value_booked = fields.Float(string='Value (Booked)', readonly=True)
    moving_avg_cost = fields.Float(string='Moving-Avg Cost', readonly=True,
                                   aggregator='avg')
    value_moving_avg = fields.Float(string='Value (Moving Avg)',
                                    readonly=True)

    def action_open_card(self):
        """Drill from a status line into the live Stock Card ledger for
        this product."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Card — %s' % self.product_id.display_name,
            'res_model': 'report.pharmacy.stock.card',
            'view_mode': 'list',
            'domain': [('product_id', '=', self.product_id.id)],
            'target': 'current',
        }

    def action_open_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
