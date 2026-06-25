# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyPosControl(models.Model):
    """POS session control / Z-report and cash reconciliation."""
    _name = 'report.pharmacy.pos.control'
    _description = 'Pharmacy POS Control Report'
    _auto = False
    _order = 'start_at desc'

    session_id = fields.Many2one('pos.session', string='Session',
                                 readonly=True)
    config_id = fields.Many2one('pos.config', string='POS Point',
                                readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    user_id = fields.Many2one('res.users', string='Responsible',
                              readonly=True)
    start_at = fields.Datetime(string='Opened', readonly=True)
    stop_at = fields.Datetime(string='Closed', readonly=True)
    state = fields.Selection(
        selection=[
            ('opening_control', 'Opening Control'),
            ('opened', 'In Progress'),
            ('closing_control', 'Closing Control'),
            ('closed', 'Closed & Posted'),
        ], string='Status', readonly=True)
    opening_cash = fields.Float(string='Opening Cash', readonly=True)
    closing_cash_expected = fields.Float(string='Expected Closing Cash',
                                         readonly=True)
    closing_cash_real = fields.Float(string='Counted Closing Cash',
                                     readonly=True)
    cash_difference = fields.Float(string='Cash Difference', readonly=True)
    order_count = fields.Integer(string='Orders', readonly=True)
    session_revenue = fields.Float(string='Session Revenue', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    s.id AS id,
                    s.id AS session_id,
                    s.config_id AS config_id,
                    s.branch_id AS branch_id,
                    s.user_id AS user_id,
                    s.start_at AS start_at,
                    s.stop_at AS stop_at,
                    s.state AS state,
                    COALESCE(s.cash_register_balance_start, 0.0)
                        AS opening_cash,
                    (COALESCE(s.cash_register_balance_start, 0.0)
                     + COALESCE(cash.amount, 0.0))
                        AS closing_cash_expected,
                    COALESCE(s.cash_register_balance_end_real, 0.0)
                        AS closing_cash_real,
                    (COALESCE(s.cash_register_balance_end_real, 0.0)
                     - (COALESCE(s.cash_register_balance_start, 0.0)
                        + COALESCE(cash.amount, 0.0)))
                        AS cash_difference,
                    COALESCE(ord.cnt, 0) AS order_count,
                    COALESCE(ord.revenue, 0.0) AS session_revenue,
                    c.company_id AS company_id
                FROM pos_session s
                JOIN pos_config c ON c.id = s.config_id
                LEFT JOIN (
                    SELECT session_id,
                           COUNT(id) AS cnt,
                           SUM(amount_total) AS revenue
                    FROM pos_order
                    WHERE state IN ('paid', 'done', 'invoiced')
                    GROUP BY session_id
                ) ord ON ord.session_id = s.id
                LEFT JOIN (
                    SELECT pay.session_id,
                           SUM(pay.amount) AS amount
                    FROM pos_payment pay
                    JOIN pos_payment_method pm
                        ON pay.payment_method_id = pm.id
                    WHERE pm.is_cash_count = TRUE
                    GROUP BY pay.session_id
                ) cash ON cash.session_id = s.id
            )
        """ % self._table)


class ReportPharmacyPayment(models.Model):
    """Payment method analysis report."""
    _name = 'report.pharmacy.payment'
    _description = 'Pharmacy Payment Method Analysis'
    _auto = False
    _order = 'amount_total desc'

    payment_method_id = fields.Many2one(
        'pos.payment.method', string='Payment Method', readonly=True)
    session_id = fields.Many2one('pos.session', string='Session',
                                 readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    payment_date = fields.Datetime(string='Date', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    payment_count = fields.Integer(string='Transactions', readonly=True)
    amount_total = fields.Float(string='Total Amount', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(pay.id) AS id,
                    pay.payment_method_id AS payment_method_id,
                    pay.session_id AS session_id,
                    o.branch_id AS branch_id,
                    DATE_TRUNC('day', pay.payment_date) AS payment_date,
                    o.company_id AS company_id,
                    COUNT(pay.id) AS payment_count,
                    SUM(pay.amount) AS amount_total
                FROM pos_payment pay
                JOIN pos_order o ON pay.pos_order_id = o.id
                WHERE o.state IN ('paid', 'done', 'invoiced')
                GROUP BY pay.payment_method_id, pay.session_id,
                         o.branch_id, DATE_TRUNC('day', pay.payment_date),
                         o.company_id
            )
        """ % self._table)


class ReportPharmacyRefund(models.Model):
    """Refund & void transaction report."""
    _name = 'report.pharmacy.refund'
    _description = 'Pharmacy Refund & Void Report'
    _auto = False
    _order = 'order_date desc'

    order_id = fields.Many2one('pos.order', string='POS Order',
                               readonly=True)
    order_date = fields.Datetime(string='Date', readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    refund_amount = fields.Float(string='Refund Amount', readonly=True)
    note = fields.Char(string='Reason / Note', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    o.id AS id,
                    o.id AS order_id,
                    o.date_order AS order_date,
                    o.branch_id AS branch_id,
                    o.user_id AS user_id,
                    o.partner_id AS partner_id,
                    o.company_id AS company_id,
                    o.amount_total AS refund_amount,
                    NULL::varchar AS note
                FROM pos_order o
                WHERE o.amount_total < 0
                  AND o.state IN ('paid', 'done', 'invoiced')
            )
        """ % self._table)
