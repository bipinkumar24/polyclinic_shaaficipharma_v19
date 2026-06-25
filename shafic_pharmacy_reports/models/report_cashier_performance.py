# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyCashierPerformance(models.Model):
    """Sales by cashier / pharmacist."""
    _name = 'report.pharmacy.cashier.performance'
    _description = 'Pharmacy Cashier / Pharmacist Performance'
    _auto = False
    _order = 'revenue desc'

    cashier_id = fields.Many2one('res.users', string='Cashier',
                                 readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    order_date = fields.Datetime(string='Date', readonly=True)
    revenue = fields.Float(string='Sales Generated', readonly=True)
    discount_total = fields.Float(string='Discount Given', readonly=True)
    refund_total = fields.Float(string='Refund Value', readonly=True)
    transaction_count = fields.Integer(string='Transactions', readonly=True)
    avg_ticket = fields.Float(string='Average Ticket Size', readonly=True,
                              aggregator='avg')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(o.id) AS id,
                    o.user_id AS cashier_id,
                    o.branch_id AS branch_id,
                    o.company_id AS company_id,
                    DATE_TRUNC('day', o.date_order) AS order_date,
                    SUM(CASE WHEN o.amount_total >= 0
                             THEN o.amount_total ELSE 0.0 END) AS revenue,
                    SUM(COALESCE(ld.discount_total, 0.0)) AS discount_total,
                    SUM(CASE WHEN o.amount_total < 0
                             THEN o.amount_total ELSE 0.0 END) AS refund_total,
                    COUNT(DISTINCT o.id) AS transaction_count,
                    CASE WHEN COUNT(DISTINCT o.id) <> 0
                         THEN SUM(o.amount_total) / COUNT(DISTINCT o.id)
                         ELSE 0.0 END AS avg_ticket
                FROM pos_order o
                LEFT JOIN (
                    SELECT order_id,
                           SUM(price_unit * qty * discount / 100.0)
                               AS discount_total
                    FROM pos_order_line
                    WHERE discount > 0
                    GROUP BY order_id
                ) ld ON ld.order_id = o.id
                WHERE o.state IN ('paid', 'done', 'invoiced')
                GROUP BY o.user_id, o.branch_id, o.company_id,
                         DATE_TRUNC('day', o.date_order)
            )
        """ % self._table)
