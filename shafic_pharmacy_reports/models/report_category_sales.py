# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyCategorySales(models.Model):
    """Sales aggregation by pharmacy category."""
    _name = 'report.pharmacy.category.sales'
    _description = 'Pharmacy Category Sales Report'
    _auto = False
    _order = 'revenue desc'

    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    order_date = fields.Datetime(string='Order Date', readonly=True)
    qty_sold = fields.Float(string='Quantity', readonly=True)
    revenue = fields.Float(string='Sales Value', readonly=True)
    margin = fields.Float(string='Margin', readonly=True)
    margin_percent = fields.Float(string='Margin %', readonly=True,
                                  aggregator='avg')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(l.id) AS id,
                    t.pharmacy_category_id AS pharmacy_category_id,
                    o.branch_id AS branch_id,
                    o.company_id AS company_id,
                    DATE_TRUNC('day', o.date_order) AS order_date,
                    SUM(l.qty) AS qty_sold,
                    SUM(l.price_subtotal) AS revenue,
                    SUM(l.price_subtotal - COALESCE(l.total_cost, 0.0))
                        AS margin,
                    CASE WHEN SUM(l.price_subtotal) <> 0
                         THEN (SUM(l.price_subtotal -
                                   COALESCE(l.total_cost, 0.0))
                               / SUM(l.price_subtotal)) * 100.0
                         ELSE 0.0 END AS margin_percent
                FROM pos_order_line l
                JOIN pos_order o ON l.order_id = o.id
                JOIN product_product p ON l.product_id = p.id
                JOIN product_template t ON p.product_tmpl_id = t.id
                WHERE o.state IN ('paid', 'done', 'invoiced')
                GROUP BY t.pharmacy_category_id, o.branch_id, o.company_id,
                         DATE_TRUNC('day', o.date_order)
            )
        """ % self._table)
