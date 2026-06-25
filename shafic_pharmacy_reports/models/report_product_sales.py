# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class ReportPharmacyProductSales(models.Model):
    """Per-product sales aggregation for top/low/dead stock analysis."""
    _name = 'report.pharmacy.product.sales'
    _description = 'Pharmacy Product Sales Analysis'
    _auto = False
    _rec_name = 'product_id'
    _order = 'revenue desc'

    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    categ_id = fields.Many2one('product.category', string='Category',
                               readonly=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    qty_sold = fields.Float(string='Quantity Sold', readonly=True)
    revenue = fields.Float(string='Revenue', readonly=True)
    cost = fields.Float(string='Cost', readonly=True)
    margin = fields.Float(string='Margin Value', readonly=True)
    margin_percent = fields.Float(string='Profit %', readonly=True,
                                  aggregator='avg')
    avg_price = fields.Float(string='Avg Selling Price', readonly=True,
                             aggregator='avg')
    order_count = fields.Integer(string='Order Count', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(l.id) AS id,
                    l.product_id AS product_id,
                    t.categ_id AS categ_id,
                    t.pharmacy_category_id AS pharmacy_category_id,
                    o.branch_id AS branch_id,
                    o.company_id AS company_id,
                    SUM(l.qty) AS qty_sold,
                    SUM(l.price_subtotal) AS revenue,
                    SUM(COALESCE(l.total_cost, 0.0)) AS cost,
                    SUM(l.price_subtotal - COALESCE(l.total_cost, 0.0))
                        AS margin,
                    CASE WHEN SUM(l.price_subtotal) <> 0
                         THEN (SUM(l.price_subtotal -
                                   COALESCE(l.total_cost, 0.0))
                               / SUM(l.price_subtotal)) * 100.0
                         ELSE 0.0 END AS margin_percent,
                    CASE WHEN SUM(l.qty) <> 0
                         THEN SUM(l.price_subtotal) / SUM(l.qty)
                         ELSE 0.0 END AS avg_price,
                    COUNT(DISTINCT o.id) AS order_count
                FROM pos_order_line l
                JOIN pos_order o ON l.order_id = o.id
                JOIN product_product p ON l.product_id = p.id
                JOIN product_template t ON p.product_tmpl_id = t.id
                WHERE o.state IN ('paid', 'done', 'invoiced')
                GROUP BY l.product_id, t.categ_id, t.pharmacy_category_id,
                         o.branch_id, o.company_id
            )
        """ % self._table)
