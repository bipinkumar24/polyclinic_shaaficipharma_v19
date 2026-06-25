# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyProfitability(models.Model):
    """Profitability analytics - product/category margin and discount impact.

    One row per POS order line so margin, discount and category dimensions
    can be sliced freely in pivot views.
    """
    _name = 'report.pharmacy.profitability'
    _description = 'Pharmacy Profitability Analysis'
    _auto = False
    _order = 'order_date desc'

    order_id = fields.Many2one('pos.order', string='POS Order',
                               readonly=True)
    order_date = fields.Datetime(string='Order Date', readonly=True)
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
    qty = fields.Float(string='Quantity', readonly=True)
    selling_price = fields.Float(string='Selling Price', readonly=True,
                                 aggregator='avg')
    unit_cost = fields.Float(string='Unit Cost', readonly=True,
                             aggregator='avg')
    revenue = fields.Float(string='Revenue', readonly=True)
    cost = fields.Float(string='Cost', readonly=True)
    margin_value = fields.Float(string='Margin Value', readonly=True)
    margin_percent = fields.Float(string='Margin %', readonly=True,
                                  aggregator='avg')
    discount_amount = fields.Float(string='Discount Amount', readonly=True)
    discount_percent = fields.Float(string='Discount %', readonly=True,
                                    aggregator='avg')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    base.id AS id,
                    base.order_id AS order_id,
                    base.order_date AS order_date,
                    base.product_id AS product_id,
                    base.categ_id AS categ_id,
                    base.pharmacy_category_id AS pharmacy_category_id,
                    base.branch_id AS branch_id,
                    base.company_id AS company_id,
                    base.qty AS qty,
                    base.selling_price AS selling_price,
                    -- Per-unit cost shown = product moving-average cost.
                    base.avg_cost AS unit_cost,
                    base.revenue AS revenue,
                    -- Cost = revenue x (moving-average cost / sale price).
                    -- The ratio is independent of the sale UoM, so a
                    -- product costed per box but sold per tablet is valued
                    -- correctly. Uses the moving-average cost (never
                    -- standard_price). When avg cost is unusable (<=0 or no
                    -- price) cost shows 0.
                    base.line_cost AS cost,
                    (base.revenue - base.line_cost) AS margin_value,
                    CASE WHEN base.revenue <> 0
                         THEN ((base.revenue - base.line_cost)
                               / base.revenue) * 100.0
                         ELSE 0.0 END AS margin_percent,
                    base.discount_amount AS discount_amount,
                    base.discount_percent AS discount_percent
                FROM (
                    SELECT
                        l.id AS id,
                        o.id AS order_id,
                        o.date_order AS order_date,
                        l.product_id AS product_id,
                        t.categ_id AS categ_id,
                        t.pharmacy_category_id AS pharmacy_category_id,
                        o.branch_id AS branch_id,
                        o.company_id AS company_id,
                        l.qty AS qty,
                        l.price_unit AS selling_price,
                        l.price_subtotal AS revenue,
                        t.list_price AS price,
                        COALESCE(
                            (p.standard_price ->> o.company_id::text)::numeric,
                            0.0) AS avg_cost,
                        CASE
                            WHEN t.list_price > 0
                             AND COALESCE(
                                 (p.standard_price ->> o.company_id::text)
                                 ::numeric, 0.0) > 0
                            THEN l.price_subtotal
                                 * (COALESCE(
                                        (p.standard_price
                                         ->> o.company_id::text)::numeric, 0.0)
                                    / t.list_price)
                            ELSE 0.0
                        END AS line_cost,
                        CASE WHEN l.discount > 0
                             THEN (l.price_unit * l.qty * l.discount / 100.0)
                             ELSE 0.0 END AS discount_amount,
                        l.discount AS discount_percent
                    FROM pos_order_line l
                    JOIN pos_order o ON l.order_id = o.id
                    JOIN product_product p ON l.product_id = p.id
                    JOIN product_template t ON p.product_tmpl_id = t.id
                    WHERE o.state IN ('paid', 'done', 'invoiced')
                ) base
            )
        """ % self._table)
