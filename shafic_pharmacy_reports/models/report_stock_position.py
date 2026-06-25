# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyStockPosition(models.Model):
    """Current stock position with batch / expiry detail."""
    _name = 'report.pharmacy.stock.position'
    _description = 'Pharmacy Stock Position Report'
    _auto = False
    _order = 'product_id, expiration_date'

    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    default_code = fields.Char(string='SKU', readonly=True)
    categ_id = fields.Many2one('product.category', string='Category',
                               readonly=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Batch / Lot',
                             readonly=True)
    lot_name = fields.Char(string='Batch Number', readonly=True)
    expiration_date = fields.Datetime(string='Expiry Date', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location',
                                  readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    quantity = fields.Float(string='Available Qty', readonly=True)
    reserved_quantity = fields.Float(string='Reserved Qty', readonly=True)
    unit_cost = fields.Float(string='Unit Cost', readonly=True,
                             aggregator='avg')
    stock_value = fields.Float(string='Stock Value', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    q.id AS id,
                    q.product_id AS product_id,
                    p.default_code AS default_code,
                    t.categ_id AS categ_id,
                    t.pharmacy_category_id AS pharmacy_category_id,
                    q.lot_id AS lot_id,
                    sl.name AS lot_name,
                    sl.expiration_date AS expiration_date,
                    q.location_id AS location_id,
                    wh.id AS warehouse_id,
                    q.company_id AS company_id,
                    q.quantity AS quantity,
                    q.reserved_quantity AS reserved_quantity,
                    COALESCE(
                        (p.standard_price ->> q.company_id::text)::numeric,
                        0.0) AS unit_cost,
                    q.quantity * COALESCE(
                        (p.standard_price ->> q.company_id::text)::numeric,
                        0.0) AS stock_value
                FROM stock_quant q
                JOIN stock_location loc ON q.location_id = loc.id
                JOIN product_product p ON q.product_id = p.id
                JOIN product_template t ON p.product_tmpl_id = t.id
                LEFT JOIN stock_lot sl ON q.lot_id = sl.id
                LEFT JOIN stock_warehouse wh
                    ON wh.lot_stock_id = loc.id
                    OR loc.parent_path LIKE '%%/' || wh.view_location_id
                       || '/%%'
                WHERE loc.usage = 'internal'
                  AND q.quantity <> 0
            )
        """ % self._table)
