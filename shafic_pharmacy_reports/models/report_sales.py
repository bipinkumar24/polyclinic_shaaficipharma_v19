# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class ReportPharmacySales(models.Model):
    """POS sales analysis aggregated per order line for pharmacy reporting.

    Backed by a SQL view so it can be queried efficiently in list, pivot
    and graph views without storing duplicate data.
    """
    _name = 'report.pharmacy.sales'
    _description = 'Pharmacy POS Sales Report'
    _auto = False
    _rec_name = 'order_date'
    _order = 'order_date desc'

    order_id = fields.Many2one('pos.order', string='POS Order', readonly=True)
    order_date = fields.Datetime(string='Order Date', readonly=True)
    session_id = fields.Many2one(
        'pos.session', string='POS Session', readonly=True)
    config_id = fields.Many2one('pos.config', string='POS Point',
                                readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    cashier_id = fields.Many2one('res.users', string='Cashier',
                                 readonly=True)
    pharmacist_id = fields.Many2one('res.users', string='Pharmacist',
                                    readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 readonly=True)
    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category',
                               readonly=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    qty = fields.Float(string='Quantity', readonly=True)
    price_subtotal = fields.Float(string='Net Sales', readonly=True)
    price_total = fields.Float(string='Gross Sales', readonly=True)
    tax_amount = fields.Float(string='Taxes', readonly=True)
    discount_amount = fields.Float(string='Discounts', readonly=True)
    margin = fields.Float(string='Margin', readonly=True)
    cost = fields.Float(string='Cost', readonly=True)
    is_refund = fields.Boolean(string='Is Refund', readonly=True)
    state = fields.Selection(
        selection=[
            ('draft', 'New'),
            ('paid', 'Paid'),
            ('done', 'Posted'),
            ('invoiced', 'Invoiced'),
            ('cancel', 'Cancelled'),
        ], string='Status', readonly=True)

    def _select(self):
        return """
            l.id AS id,
            o.id AS order_id,
            o.date_order AS order_date,
            o.session_id AS session_id,
            o.config_id AS config_id,
            o.branch_id AS branch_id,
            o.user_id AS cashier_id,
            o.pharmacist_id AS pharmacist_id,
            o.partner_id AS partner_id,
            l.product_id AS product_id,
            t.categ_id AS categ_id,
            t.pharmacy_category_id AS pharmacy_category_id,
            o.company_id AS company_id,
            o.state AS state,
            l.qty AS qty,
            l.price_subtotal AS price_subtotal,
            l.price_subtotal_incl AS price_total,
            (l.price_subtotal_incl - l.price_subtotal) AS tax_amount,
            CASE WHEN l.discount > 0
                 THEN (l.price_unit * l.qty * l.discount / 100.0)
                 ELSE 0.0 END AS discount_amount,
            (l.price_subtotal - (COALESCE(l.total_cost, 0.0))) AS margin,
            COALESCE(l.total_cost, 0.0) AS cost,
            CASE WHEN l.qty < 0 THEN TRUE ELSE FALSE END AS is_refund
        """

    def _from(self):
        return """
            pos_order_line l
            JOIN pos_order o ON l.order_id = o.id
            JOIN product_product p ON l.product_id = p.id
            JOIN product_template t ON p.product_tmpl_id = t.id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT %s FROM %s
            )
        """ % (self._table, self._select(), self._from()))
