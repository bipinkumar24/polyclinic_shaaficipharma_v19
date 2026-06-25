# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyStockCard(models.Model):
    """Inventory Stock Card — a per-product item ledger.

    One row per stock movement (receipt, sale, adjustment), in date
    order, with running quantity and running value balances per product —
    the QuickBooks-style "Inventory Valuation Detail" / stock card.

    Source is stock.move (done moves where exactly one side is an internal
    location, i.e. a real in/out of on-hand stock). Each move is valued at
    the product's cost (standard_price), so the report carries no
    dependency on stock_account / stock_valuation_layer and works whether
    or not Inventory Valuation is installed. The running balances are
    computed with window functions over the full history, so filtering the
    search by a date range still shows the correct cumulative balance at
    each line (the balance includes everything before the visible window).
    """
    _name = 'report.pharmacy.stock.card'
    _description = 'Inventory Stock Card'
    _auto = False
    _order = 'date desc, id desc'

    date = fields.Datetime(string='Date', readonly=True)
    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    categ_id = fields.Many2one('product.category', string='Category',
                               readonly=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    reference = fields.Char(string='Reference', readonly=True)
    move_kind = fields.Selection(
        selection=[('in', 'In'), ('out', 'Out'), ('adjust', 'Adjustment')],
        string='Type', readonly=True)
    qty_in = fields.Float(string='Qty In', readonly=True)
    qty_out = fields.Float(string='Qty Out', readonly=True)
    balance_qty = fields.Float(string='Balance Qty', readonly=True)
    value = fields.Float(string='Value Change', readonly=True)
    balance_value = fields.Float(string='Balance Value', readonly=True)
    unit_cost = fields.Float(string='Unit Cost', readonly=True,
                             aggregator='avg')
    stock_move_id = fields.Many2one('stock.move', string='Move',
                                    readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Transfer',
                                 readonly=True)

    def action_open_source(self):
        """Open the source document behind this ledger line — the
        transfer/picking if there is one, else the raw stock move. Covers
        receipts, deliveries, POS sales, returns and adjustments."""
        self.ensure_one()
        if self.picking_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': self.picking_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'res_id': self.stock_move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    base.id AS id,
                    base.date AS date,
                    base.product_id AS product_id,
                    base.categ_id AS categ_id,
                    base.pharmacy_category_id AS pharmacy_category_id,
                    base.company_id AS company_id,
                    base.reference AS reference,
                    base.stock_move_id AS stock_move_id,
                    base.picking_id AS picking_id,
                    base.move_kind AS move_kind,
                    base.qty_in AS qty_in,
                    base.qty_out AS qty_out,
                    SUM(base.signed_qty) OVER (
                        PARTITION BY base.product_id, base.company_id
                        ORDER BY base.date, base.id
                    ) AS balance_qty,
                    base.value AS value,
                    SUM(base.value) OVER (
                        PARTITION BY base.product_id, base.company_id
                        ORDER BY base.date, base.id
                    ) AS balance_value,
                    base.unit_cost AS unit_cost
                FROM (
                    SELECT
                        sm.id AS id,
                        sm.date AS date,
                        sm.product_id AS product_id,
                        t.categ_id AS categ_id,
                        t.pharmacy_category_id AS pharmacy_category_id,
                        sm.company_id AS company_id,
                        COALESCE(sm.reference) AS reference,
                        sm.id AS stock_move_id,
                        sm.picking_id AS picking_id,
                        CASE
                            WHEN dest.usage = 'internal'
                                 AND src.usage <> 'internal' THEN 'in'
                            WHEN src.usage = 'internal'
                                 AND dest.usage <> 'internal' THEN 'out'
                            ELSE 'adjust'
                        END AS move_kind,
                        CASE WHEN dest.usage = 'internal'
                                  AND src.usage <> 'internal'
                             THEN sm.product_qty ELSE 0.0 END AS qty_in,
                        CASE WHEN src.usage = 'internal'
                                  AND dest.usage <> 'internal'
                             THEN sm.product_qty ELSE 0.0 END AS qty_out,
                        CASE
                            WHEN dest.usage = 'internal'
                                 AND src.usage <> 'internal'
                                THEN sm.product_qty
                            WHEN src.usage = 'internal'
                                 AND dest.usage <> 'internal'
                                THEN -sm.product_qty
                            ELSE 0.0
                        END AS signed_qty,
                        CASE
                            WHEN dest.usage = 'internal'
                                 AND src.usage <> 'internal'
                                THEN sm.product_qty
                            WHEN src.usage = 'internal'
                                 AND dest.usage <> 'internal'
                                THEN -sm.product_qty
                            ELSE 0.0
                        END * COALESCE(
                            (p.standard_price ->> sm.company_id::text)
                            ::numeric, 0.0) AS value,
                        COALESCE(
                            (p.standard_price ->> sm.company_id::text)
                            ::numeric, 0.0) AS unit_cost
                    FROM stock_move sm
                    JOIN product_product p ON sm.product_id = p.id
                    JOIN product_template t ON p.product_tmpl_id = t.id
                    JOIN stock_location src ON sm.location_id = src.id
                    JOIN stock_location dest ON sm.location_dest_id = dest.id
                    WHERE sm.state = 'done'
                      AND (
                          (dest.usage = 'internal'
                           AND src.usage <> 'internal')
                          OR (src.usage = 'internal'
                              AND dest.usage <> 'internal')
                      )
                ) base
            )
        """ % self._table)
