# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyReorder(models.Model):
    """Reorder report with demand-driven procurement suggestions.

    Suggested order quantity uses actual recent demand and supplier
    lead time, not a flat min/max difference. The model writes back to
    a SQL view that joins trailing-90-day POS sales and supplier delay.
    """
    _name = 'report.pharmacy.reorder'
    _description = 'Pharmacy Reorder Level Report'
    _auto = False
    _order = 'shortage desc'

    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    categ_id = fields.Many2one('product.category', string='Category',
                               readonly=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    qty_available = fields.Float(string='Available Qty', readonly=True)
    reorder_min = fields.Float(string='Reorder Minimum', readonly=True)
    reorder_max = fields.Float(string='Reorder Maximum', readonly=True)
    shortage = fields.Float(string='Shortage', readonly=True)

    avg_daily_demand = fields.Float(
        string='Avg Daily Demand', readonly=True, digits=(8, 2),
        help='Average units sold per day over the trailing 90 days.')
    lead_time_days = fields.Integer(
        string='Lead Time (Days)', readonly=True,
        help='Supplier delivery lead time from product.supplierinfo. '
             'Defaults to 7 days when no supplier delay is recorded.')
    days_of_cover = fields.Float(
        string='Days of Cover', readonly=True, digits=(8, 1),
        help='How many days the current on-hand quantity will last at '
             'the current average daily demand.')
    suggested_qty = fields.Float(
        string='Suggested Order Qty', readonly=True,
        help='Demand-driven recommendation: average daily demand x '
             '(lead time + 7 day safety buffer), minus current on-hand. '
             'Capped at the reorder maximum where one is set.')
    needs_reorder = fields.Boolean(string='Needs Reorder', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    p.id AS id,
                    p.id AS product_id,
                    t.categ_id AS categ_id,
                    t.pharmacy_category_id AS pharmacy_category_id,
                    t.company_id AS company_id,
                    COALESCE(oh.qty, 0.0) AS qty_available,
                    COALESCE(t.reorder_min_qty, 0.0) AS reorder_min,
                    COALESCE(t.reorder_max_qty, 0.0) AS reorder_max,
                    GREATEST(COALESCE(t.reorder_min_qty, 0.0)
                             - COALESCE(oh.qty, 0.0), 0.0) AS shortage,
                    COALESCE(sales.avg_daily, 0.0) AS avg_daily_demand,
                    COALESCE(sup.lead_days, 7) AS lead_time_days,
                    CASE WHEN COALESCE(sales.avg_daily, 0.0) > 0
                         THEN COALESCE(oh.qty, 0.0) / sales.avg_daily
                         ELSE NULL END AS days_of_cover,
                    CASE
                        WHEN COALESCE(sales.avg_daily, 0.0) > 0 THEN
                            GREATEST(
                                LEAST(
                                    sales.avg_daily
                                        * (COALESCE(sup.lead_days, 7) + 7)
                                        - COALESCE(oh.qty, 0.0),
                                    CASE WHEN COALESCE(t.reorder_max_qty, 0.0)
                                              > 0
                                         THEN COALESCE(t.reorder_max_qty, 0.0)
                                              - COALESCE(oh.qty, 0.0)
                                         ELSE
                                            sales.avg_daily
                                                * (COALESCE(sup.lead_days, 7)
                                                   + 7)
                                                - COALESCE(oh.qty, 0.0)
                                    END),
                                0.0)
                        WHEN COALESCE(oh.qty, 0.0)
                              < COALESCE(t.reorder_min_qty, 0.0) THEN
                            GREATEST(COALESCE(t.reorder_max_qty, 0.0)
                                     - COALESCE(oh.qty, 0.0), 0.0)
                        ELSE 0.0
                    END AS suggested_qty,
                    CASE WHEN COALESCE(oh.qty, 0.0)
                              < COALESCE(t.reorder_min_qty, 0.0)
                         THEN TRUE ELSE FALSE END AS needs_reorder
                FROM product_product p
                JOIN product_template t ON p.product_tmpl_id = t.id
                LEFT JOIN (
                    SELECT q.product_id, SUM(q.quantity) AS qty
                    FROM stock_quant q
                    JOIN stock_location loc ON q.location_id = loc.id
                    WHERE loc.usage = 'internal'
                    GROUP BY q.product_id
                ) oh ON oh.product_id = p.id
                LEFT JOIN (
                    SELECT l.product_id, SUM(l.qty) / 90.0 AS avg_daily
                    FROM pos_order_line l
                    JOIN pos_order o ON l.order_id = o.id
                    WHERE o.state IN ('paid', 'done', 'invoiced')
                      AND o.date_order >= (CURRENT_DATE - INTERVAL '90 days')
                    GROUP BY l.product_id
                ) sales ON sales.product_id = p.id
                LEFT JOIN (
                    SELECT product_tmpl_id, MIN(delay) AS lead_days
                    FROM product_supplierinfo
                    WHERE delay IS NOT NULL
                    GROUP BY product_tmpl_id
                ) sup ON sup.product_tmpl_id = t.id
                WHERE t.reorder_min_qty > 0
                   OR COALESCE(sales.avg_daily, 0.0) > 0
            )
        """ % self._table)
