# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacySupplierPerformance(models.Model):
    """Supplier performance & purchase-vs-sales reporting."""
    _name = 'report.pharmacy.supplier.performance'
    _description = 'Pharmacy Supplier Performance Report'
    _auto = False
    _order = 'total_purchased desc'

    supplier_id = fields.Many2one('res.partner', string='Supplier',
                                  readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    order_count = fields.Integer(string='Purchase Orders', readonly=True)
    line_count = fields.Integer(string='Order Lines', readonly=True)
    total_purchased = fields.Float(string='Total Purchased', readonly=True)
    qty_purchased = fields.Float(string='Qty Purchased', readonly=True)
    qty_received = fields.Float(string='Qty Received', readonly=True)
    delivery_accuracy = fields.Float(
        string='Delivery Accuracy %', readonly=True, aggregator='avg')
    avg_lead_time = fields.Float(string='Avg Lead Time (days)',
                                 readonly=True, aggregator='avg')
    on_time_rate = fields.Float(string='On-Time Rate %', readonly=True,
                                aggregator='avg')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    po.partner_id AS id,
                    po.partner_id AS supplier_id,
                    po.company_id AS company_id,
                    COUNT(DISTINCT po.id) AS order_count,
                    COUNT(pol.id) AS line_count,
                    SUM(pol.price_subtotal) AS total_purchased,
                    SUM(pol.product_qty) AS qty_purchased,
                    SUM(pol.qty_received) AS qty_received,
                    CASE WHEN SUM(pol.product_qty) <> 0
                         THEN (SUM(pol.qty_received)
                               / SUM(pol.product_qty)) * 100.0
                         ELSE 0.0 END AS delivery_accuracy,
                    AVG(CASE
                        WHEN po.date_approve IS NOT NULL
                             AND pol.date_planned IS NOT NULL
                        THEN EXTRACT(EPOCH FROM
                             (pol.date_planned - po.date_approve)) / 86400.0
                        ELSE NULL END) AS avg_lead_time,
                    CASE WHEN COUNT(pol.id) <> 0
                         THEN (SUM(CASE WHEN pol.qty_received
                                             >= pol.product_qty
                                        THEN 1 ELSE 0 END)::numeric
                               / COUNT(pol.id)) * 100.0
                         ELSE 0.0 END AS on_time_rate
                FROM purchase_order po
                JOIN purchase_order_line pol ON pol.order_id = po.id
                WHERE po.state IN ('purchase', 'done')
                GROUP BY po.partner_id, po.company_id
            )
        """ % self._table)


class ReportPharmacyPurchaseVsSales(models.Model):
    """Purchase vs Sales comparison per product."""
    _name = 'report.pharmacy.purchase.sales'
    _description = 'Pharmacy Purchase vs Sales Report'
    _auto = False
    _order = 'product_id'

    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    qty_purchased = fields.Float(string='Qty Purchased', readonly=True)
    purchase_value = fields.Float(string='Purchase Value', readonly=True)
    qty_sold = fields.Float(string='Qty Sold', readonly=True)
    sales_value = fields.Float(string='Sales Value', readonly=True)
    gross_margin = fields.Float(string='Gross Margin', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    p.id AS id,
                    p.id AS product_id,
                    t.company_id AS company_id,
                    COALESCE(pur.qty, 0.0) AS qty_purchased,
                    COALESCE(pur.val, 0.0) AS purchase_value,
                    COALESCE(sal.qty, 0.0) AS qty_sold,
                    COALESCE(sal.val, 0.0) AS sales_value,
                    (COALESCE(sal.val, 0.0) - COALESCE(sal.cost, 0.0))
                        AS gross_margin
                FROM product_product p
                JOIN product_template t ON p.product_tmpl_id = t.id
                LEFT JOIN (
                    SELECT pol.product_id,
                           SUM(pol.qty_received) AS qty,
                           SUM(pol.price_subtotal) AS val
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE po.state IN ('purchase', 'done')
                    GROUP BY pol.product_id
                ) pur ON pur.product_id = p.id
                LEFT JOIN (
                    SELECT l.product_id,
                           SUM(l.qty) AS qty,
                           SUM(l.price_subtotal) AS val,
                           SUM(COALESCE(l.total_cost, 0.0)) AS cost
                    FROM pos_order_line l
                    JOIN pos_order o ON l.order_id = o.id
                    WHERE o.state IN ('paid', 'done', 'invoiced')
                    GROUP BY l.product_id
                ) sal ON sal.product_id = p.id
                WHERE pur.product_id IS NOT NULL
                   OR sal.product_id IS NOT NULL
            )
        """ % self._table)
