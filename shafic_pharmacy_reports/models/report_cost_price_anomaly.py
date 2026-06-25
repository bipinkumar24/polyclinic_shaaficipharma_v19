# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class ReportPharmacyCostPriceAnomaly(models.Model):
    """Cost / Price Anomaly Detection.

    Flags products whose cost and selling price look wrong, before
    those problems erode margin. Four checks run on every active
    stockable product:

      1. Static: cost >= price (Critical) — selling at or below cost.
      2. Static: margin < 10%  (Review)   — thin margin warning.
      3. Behavioural: cost spike vs own 90-day trailing average
                                (Warning) — supplier increase not yet
                                            passed through to price.
      4. Peer: margin > 1.5 sigma from category median
                                (Review)  — outlier within category.

    A product appears in the report only if it is flagged by at least
    one check. An empty list is good news. Severity drives the highest-
    priority issue: Critical > Warning > Review.
    """
    _name = 'report.pharmacy.cost.price.anomaly'
    _description = 'Pharmacy Cost / Price Anomaly Detection'
    _auto = False
    _order = 'severity_rank, product_id'

    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    product_tmpl_id = fields.Many2one('product.template',
                                      string='Product Template',
                                      readonly=True)
    categ_id = fields.Many2one('product.category', string='Category',
                               readonly=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)

    current_cost = fields.Float(
        string='Effective Cost', readonly=True, digits=(12, 4),
        help='Weighted-average cost across all warehouses (from the '
             'Warehouse-Wise Cost module), with fallback to standard '
             'price when no warehouse data is available. This is the '
             'figure used in the margin calculation.')
    standard_cost = fields.Float(
        string='Standard Cost', readonly=True, digits=(12, 4),
        help="Odoo's product.standard_price for this product/company. "
             'Shown side-by-side with the Effective Cost so '
             'discrepancies between the two are visible at a glance.')
    cost_variance_pct = fields.Float(
        string='Cost Variance %', readonly=True, digits=(8, 2),
        help='How far Standard Cost is from Effective Cost as a '
             'percentage: (effective - standard) / standard * 100. '
             'Large positive = standard is much lower than the '
             'real warehouse cost; large negative = standard is '
             'much higher.')
    current_price = fields.Float(string='Current Price', readonly=True,
                                 digits=(12, 4))
    margin_pct = fields.Float(string='Margin %', readonly=True, digits=(8, 2),
                              help='Current selling margin: '
                                   '(price - effective_cost) / price * 100.')

    avg_cost_90d = fields.Float(string='Avg Cost (90d)', readonly=True,
                                digits=(12, 4),
                                help='Average product cost over the '
                                     'trailing 90 days, computed from '
                                     'stock-move price valuations.')
    cost_change_pct = fields.Float(string='Cost Change %', readonly=True,
                                   digits=(8, 2),
                                   help='Current cost vs trailing 90-day '
                                        'average, as a percentage. '
                                        'Positive = cost has risen.')

    category_median_margin = fields.Float(
        string='Category Median Margin %', readonly=True, digits=(8, 2),
        help='Median margin across all priced products in the same '
             'pharmacy category. Anchor for peer comparison.')

    # Flags - one per check
    flag_below_cost = fields.Boolean(
        string='Selling Below Cost', readonly=True,
        help='Current price is less than or equal to current cost.')
    flag_thin_margin = fields.Boolean(
        string='Thin Margin (<10%)', readonly=True,
        help='Margin is positive but below 10%.')
    flag_cost_spike = fields.Boolean(
        string='Cost Spike', readonly=True,
        help='Current cost is at least 25% higher than the trailing '
             '90-day average.')
    flag_peer_outlier = fields.Boolean(
        string='Peer Outlier', readonly=True,
        help='Margin is far from the category median (more than '
             '1.5x median in either direction).')

    severity = fields.Selection(
        selection=[
            ('critical', 'Critical'),
            ('warning', 'Warning'),
            ('review', 'Review'),
        ], string='Severity', readonly=True,
        help='Highest severity among the flags that fired: '
             'Critical (below cost) > Warning (cost spike) > Review '
             '(thin margin or peer outlier).')
    severity_rank = fields.Integer(string='Severity Rank', readonly=True,
                                   help='1=Critical, 2=Warning, 3=Review. '
                                        'Used for sort order.')

    cost_source = fields.Selection(
        selection=[
            ('warehouse', 'Warehouse-Wise Cost'),
            ('standard', 'Standard Price (Fallback)'),
            ('zero', 'No Cost Data'),
        ], string='Cost Source', readonly=True,
        help='Where the cost figure came from. Products with "No Cost Data" '
             'are never flagged for below-cost or margin issues, since the '
             'comparison would not be meaningful.')

    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # Note: cost is now read from the product_effective_cost view,
        # which computes a weighted average across warehouses using
        # sh.warehouse.cost (the Warehouse-Wise Cost module). Falls back
        # to standard_price when warehouse-cost data is unavailable.
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH base AS (
                    SELECT
                        p.id AS product_id,
                        t.id AS product_tmpl_id,
                        t.categ_id AS categ_id,
                        t.pharmacy_category_id AS pharmacy_category_id,
                        t.company_id AS company_id,
                        COALESCE(pec.effective_cost, 0.0) AS current_cost,
                        COALESCE(pec.standard_price, 0.0) AS standard_cost,
                        COALESCE(pec.cost_source, 'zero') AS cost_source,
                        COALESCE(t.list_price, 0.0) AS current_price
                    FROM product_product p
                    JOIN product_template t ON p.product_tmpl_id = t.id
                    LEFT JOIN product_effective_cost pec
                           ON pec.product_id = p.id
                          AND pec.company_id = t.company_id
                    WHERE p.active = TRUE
                      AND t.type = 'consu'
                ),
                cost_history AS (
                    SELECT
                        sm.product_id,
                        sm.company_id,
                        AVG(NULLIF(sm.price_unit, 0)) AS avg_cost
                    FROM stock_move sm
                    WHERE sm.state = 'done'
                      AND sm.date >= (CURRENT_DATE - INTERVAL '90 days')
                      AND sm.price_unit IS NOT NULL
                    GROUP BY sm.product_id, sm.company_id
                ),
                priced AS (
                    SELECT b.*,
                           ch.avg_cost,
                           CASE WHEN b.current_price > 0
                                THEN ((b.current_price - b.current_cost)
                                      / b.current_price) * 100.0
                                ELSE 0.0 END AS margin_pct,
                           CASE WHEN ch.avg_cost IS NOT NULL
                                     AND ch.avg_cost > 0
                                THEN ((b.current_cost - ch.avg_cost)
                                      / ch.avg_cost) * 100.0
                                ELSE 0.0 END AS cost_change_pct
                    FROM base b
                    LEFT JOIN cost_history ch
                        ON ch.product_id = b.product_id
                       AND ch.company_id = b.company_id
                    WHERE b.current_price > 0
                       OR b.current_cost > 0
                ),
                cat_stats AS (
                    SELECT pharmacy_category_id,
                           company_id,
                           PERCENTILE_CONT(0.5) WITHIN GROUP
                               (ORDER BY margin_pct) AS median_margin,
                           COUNT(*) AS cat_size
                    FROM priced
                    WHERE current_price > 0 AND current_cost > 0
                    GROUP BY pharmacy_category_id, company_id
                ),
                flagged AS (
                    SELECT pr.*,
                           cs.median_margin AS category_median_margin,
                           cs.cat_size,
                           (pr.current_price > 0
                                AND pr.current_cost >= pr.current_price
                                AND pr.cost_source <> 'zero')
                                AS flag_below_cost,
                           (pr.current_price > 0
                                AND pr.current_cost > 0
                                AND pr.margin_pct > 0
                                AND pr.margin_pct < 10.0
                                AND pr.cost_source <> 'zero')
                                AS flag_thin_margin,
                           (pr.cost_change_pct >= 25.0
                                AND pr.cost_source <> 'zero')
                                AS flag_cost_spike,
                           (cs.cat_size >= 5
                                AND cs.median_margin IS NOT NULL
                                AND pr.current_price > 0
                                AND pr.current_cost > 0
                                AND pr.cost_source <> 'zero'
                                AND ABS(pr.margin_pct - cs.median_margin)
                                    > GREATEST(ABS(cs.median_margin) * 1.5,
                                               20.0))
                                AS flag_peer_outlier
                    FROM priced pr
                    LEFT JOIN cat_stats cs
                        ON cs.pharmacy_category_id IS NOT DISTINCT FROM
                           pr.pharmacy_category_id
                       AND cs.company_id = pr.company_id
                )
                SELECT
                    product_id AS id,
                    product_id,
                    product_tmpl_id,
                    categ_id,
                    pharmacy_category_id,
                    current_cost,
                    standard_cost,
                    CASE WHEN standard_cost > 0
                         THEN ((current_cost - standard_cost)
                               / standard_cost) * 100.0
                         ELSE 0.0
                    END AS cost_variance_pct,
                    current_price,
                    margin_pct,
                    avg_cost AS avg_cost_90d,
                    cost_change_pct,
                    category_median_margin,
                    flag_below_cost,
                    flag_thin_margin,
                    flag_cost_spike,
                    flag_peer_outlier,
                    CASE WHEN flag_below_cost THEN 'critical'
                         WHEN flag_cost_spike THEN 'warning'
                         WHEN flag_thin_margin OR flag_peer_outlier
                              THEN 'review'
                         ELSE NULL END AS severity,
                    CASE WHEN flag_below_cost THEN 1
                         WHEN flag_cost_spike THEN 2
                         WHEN flag_thin_margin OR flag_peer_outlier THEN 3
                         ELSE 99 END AS severity_rank,
                    cost_source,
                    company_id
                FROM flagged
                WHERE flag_below_cost
                   OR flag_thin_margin
                   OR flag_cost_spike
                   OR flag_peer_outlier
            )
        """ % self._table)

    def action_open_product(self):
        """Open the product form so the team can correct cost or price."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def get_anomaly_summary(self, company_id=False):
        """Return a small headline dictionary for the Executive Dashboard.

        Used by the OWL dashboard to display a clickable tile that
        summarises the report.
        """
        domain = []
        if company_id:
            domain.append(('company_id', '=', company_id))
        rows = self.search(domain)
        return {
            'total': len(rows),
            'critical': len(rows.filtered(lambda r: r.severity == 'critical')),
            'warning': len(rows.filtered(lambda r: r.severity == 'warning')),
            'review': len(rows.filtered(lambda r: r.severity == 'review')),
        }
