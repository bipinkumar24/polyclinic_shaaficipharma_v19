# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyCustomer(models.Model):
    """Customer purchase history & segmentation report."""
    _name = 'report.pharmacy.customer'
    _description = 'Pharmacy Customer Report'
    _auto = False
    _order = 'total_spend desc'

    partner_id = fields.Many2one('res.partner', string='Customer',
                                 readonly=True)
    customer_segment = fields.Selection(
        selection=[
            ('high_value', 'High Value'),
            ('frequent', 'Frequent Buyer'),
            ('insurance', 'Insurance Patient'),
            ('regular', 'Regular'),
            ('new', 'New'),
        ], string='Segment', readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    visit_count = fields.Integer(string='Visit Frequency', readonly=True)
    total_spend = fields.Float(string='Total Spend', readonly=True)
    avg_basket = fields.Float(string='Average Basket', readonly=True,
                              aggregator='avg')
    last_visit = fields.Datetime(string='Last Visit', readonly=True)
    qty_purchased = fields.Float(string='Items Purchased', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    o.partner_id AS id,
                    o.partner_id AS partner_id,
                    rp.customer_segment AS customer_segment,
                    o.branch_id AS branch_id,
                    o.company_id AS company_id,
                    COUNT(DISTINCT o.id) AS visit_count,
                    SUM(o.amount_total) AS total_spend,
                    CASE WHEN COUNT(DISTINCT o.id) <> 0
                         THEN SUM(o.amount_total) / COUNT(DISTINCT o.id)
                         ELSE 0.0 END AS avg_basket,
                    MAX(o.date_order) AS last_visit,
                    SUM(line_qty.qty) AS qty_purchased
                FROM pos_order o
                JOIN res_partner rp ON o.partner_id = rp.id
                LEFT JOIN (
                    SELECT order_id, SUM(qty) AS qty
                    FROM pos_order_line
                    GROUP BY order_id
                ) line_qty ON line_qty.order_id = o.id
                WHERE o.state IN ('paid', 'done', 'invoiced')
                  AND o.partner_id IS NOT NULL
                GROUP BY o.partner_id, rp.customer_segment,
                         o.branch_id, o.company_id
            )
        """ % self._table)


class ReportPharmacyLoyalty(models.Model):
    """Loyalty points earned / redeemed report."""
    _name = 'report.pharmacy.loyalty'
    _description = 'Pharmacy Loyalty Report'
    _auto = False
    _order = 'points_earned desc'

    partner_id = fields.Many2one('res.partner', string='Customer',
                                 readonly=True)
    program_id = fields.Many2one('loyalty.program', string='Program',
                                 readonly=True)
    points_earned = fields.Float(string='Points Earned', readonly=True)
    points_balance = fields.Float(string='Points Balance', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)

    @property
    def _loyalty_installed(self):
        return 'loyalty.card' in self.env

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # loyalty.card is provided by the 'loyalty' module which is a
        # dependency of point_of_sale; guard the table existence anyway.
        self.env.cr.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'loyalty_card'
        """)
        if self.env.cr.fetchone():
            self.env.cr.execute("""
                CREATE OR REPLACE VIEW %s AS (
                    SELECT
                        c.id AS id,
                        c.partner_id AS partner_id,
                        c.program_id AS program_id,
                        COALESCE(c.points, 0.0) AS points_earned,
                        COALESCE(c.points, 0.0) AS points_balance,
                        c.company_id AS company_id
                    FROM loyalty_card c
                    WHERE c.partner_id IS NOT NULL
                )
            """ % self._table)
        else:
            self.env.cr.execute("""
                CREATE OR REPLACE VIEW %s AS (
                    SELECT
                        0 AS id, NULL::integer AS partner_id,
                        NULL::integer AS program_id,
                        0.0 AS points_earned, 0.0 AS points_balance,
                        NULL::integer AS company_id
                    WHERE FALSE
                )
            """ % self._table)
