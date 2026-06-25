# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyBranchPerformance(models.Model):
    """Branch-level performance KPIs for multi-branch pharmacies."""
    _name = 'report.pharmacy.branch.performance'
    _description = 'Pharmacy Branch Performance Report'
    _auto = False
    _order = 'revenue desc'

    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    order_date = fields.Datetime(string='Date', readonly=True)
    revenue = fields.Float(string='Branch Revenue', readonly=True)
    margin = fields.Float(string='Profitability', readonly=True)
    order_count = fields.Integer(string='Customer Volume', readonly=True)
    avg_basket = fields.Float(string='Average Basket Size', readonly=True,
                              aggregator='avg')
    qty_sold = fields.Float(string='Units Sold', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(o.id) AS id,
                    o.branch_id AS branch_id,
                    o.company_id AS company_id,
                    DATE_TRUNC('day', o.date_order) AS order_date,
                    SUM(o.amount_total) AS revenue,
                    SUM(line_margin.margin) AS margin,
                    COUNT(DISTINCT o.id) AS order_count,
                    CASE WHEN COUNT(DISTINCT o.id) <> 0
                         THEN SUM(o.amount_total) / COUNT(DISTINCT o.id)
                         ELSE 0.0 END AS avg_basket,
                    SUM(line_margin.qty) AS qty_sold
                FROM pos_order o
                LEFT JOIN (
                    SELECT order_id,
                           SUM(price_subtotal - COALESCE(total_cost, 0.0))
                               AS margin,
                           SUM(qty) AS qty
                    FROM pos_order_line
                    GROUP BY order_id
                ) line_margin ON line_margin.order_id = o.id
                WHERE o.state IN ('paid', 'done', 'invoiced')
                  AND o.branch_id IS NOT NULL
                GROUP BY o.branch_id, o.company_id,
                         DATE_TRUNC('day', o.date_order)
            )
        """ % self._table)
