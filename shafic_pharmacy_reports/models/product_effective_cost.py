# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools
from odoo.tools import sql as sql_tools


class ProductEffectiveCost(models.Model):
    """Per-product effective cost, computed from sh_warehouse_cost.

    Background — the installed Warehouse-Wise Cost module (model
    ``sh.warehouse.cost``) intercepts Odoo's standard AVCO updates and
    writes them per-warehouse instead of to the global
    ``product.product.standard_price``. As a result, ``standard_price``
    on most products has stayed frozen at whatever value was entered at
    product creation, and reading it directly produces wildly wrong
    costs (often 3x or more above the real cost paid recently).

    This view consolidates per-warehouse costs into a single weighted
    average per product, weighted by current on-hand quantity in each
    warehouse:

        effective_cost = SUM(swc.cost * swc.sh_onhand_qty)
                         / SUM(swc.sh_onhand_qty)

    Fallbacks (applied in order):
      1. If no warehouse-cost rows exist for the product, or all
         on-hand quantities are zero, fall back to the global
         standard_price (Odoo's normal AVCO field).
      2. If standard_price is also zero, the effective cost is zero.

    All margin and valuation reports in the module read from this view
    via a ``product.effective.cost`` ORM record, or join the
    underlying SQL view ``product_effective_cost`` directly in their
    own queries.

    The view is keyed by ``id = product_id`` so the ORM can present
    one row per product. ``company_id`` is included so multi-company
    installs filter correctly (it's resolved via the warehouse).
    """
    _name = 'product.effective.cost'
    _description = 'Per-Product Effective Cost (Warehouse-Weighted)'
    _auto = False
    _order = 'product_id'

    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    effective_cost = fields.Float(string='Effective Cost', readonly=True,
                                  digits=(12, 4),
                                  help='Weighted average cost across '
                                       'all warehouses for this product, '
                                       'weighted by on-hand quantity in '
                                       'each warehouse.')
    warehouse_cost = fields.Float(string='Warehouse-Wise Cost', readonly=True,
                                  digits=(12, 4),
                                  help='The raw weighted average from '
                                       'sh.warehouse.cost. Zero when no '
                                       'on-hand stock exists across all '
                                       'warehouses.')
    standard_price = fields.Float(string='Standard Price (Fallback)',
                                  readonly=True, digits=(12, 4),
                                  help="Odoo's product.standard_price for "
                                       "this product/company. Used as "
                                       "fallback when no warehouse-cost "
                                       "data is available.")
    cost_source = fields.Selection(
        selection=[
            ('warehouse', 'Warehouse-Wise Cost'),
            ('standard', 'Standard Price (Fallback)'),
            ('zero', 'No Cost Data'),
        ], string='Cost Source', readonly=True,
        help='Which source the effective_cost came from. Use this in '
             'reports to flag products where the cost is a fallback '
             'rather than from real warehouse data.')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # Defensive: if the Warehouse-Wise Cost third-party module is
        # uninstalled, the table won't exist. Build a degraded view that
        # uses only standard_price in that case so the module still
        # installs cleanly.
        if not sql_tools.table_exists(self.env.cr, 'sh_warehouse_cost'):
            self.env.cr.execute("""
                CREATE OR REPLACE VIEW %s AS (
                    SELECT
                        p.id AS id,
                        p.id AS product_id,
                        t.company_id,
                        0.0 AS warehouse_cost,
                        COALESCE(
                            (p.standard_price->>(t.company_id::text))
                            ::numeric,
                            0.0) AS standard_price,
                        COALESCE(
                            (p.standard_price->>(t.company_id::text))
                            ::numeric,
                            0.0) AS effective_cost,
                        CASE WHEN COALESCE(
                                (p.standard_price->>(t.company_id::text))
                                ::numeric, 0.0) > 0
                             THEN 'standard'
                             ELSE 'zero'
                        END AS cost_source
                    FROM product_product p
                    JOIN product_template t ON p.product_tmpl_id = t.id
                    WHERE p.active = TRUE
                )
            """ % self._table)
            return
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH
                onhand_by_warehouse AS (
                    SELECT
                        q.product_id,
                        wh.id AS warehouse_id,
                        SUM(q.quantity) AS onhand_qty
                    FROM stock_quant q
                    JOIN stock_location loc ON loc.id = q.location_id
                        AND loc.usage = 'internal'
                    JOIN stock_warehouse wh ON (
                        loc.parent_path LIKE
                            '%%/' || wh.view_location_id::text || '/%%'
                        OR loc.id = wh.lot_stock_id
                    )
                    GROUP BY q.product_id, wh.id
                ),
                warehouse_cost AS (
                    SELECT
                        swc.product_id,
                        sw.company_id,
                        CASE WHEN SUM(COALESCE(obw.onhand_qty, 0)) > 0
                             THEN SUM(swc.cost * COALESCE(obw.onhand_qty, 0))
                                  / SUM(COALESCE(obw.onhand_qty, 0))
                             ELSE 0.0
                        END AS wh_cost
                    FROM sh_warehouse_cost swc
                    JOIN stock_warehouse sw ON sw.id = swc.warehouse_id
                    LEFT JOIN onhand_by_warehouse obw
                           ON obw.product_id = swc.product_id
                          AND obw.warehouse_id = swc.warehouse_id
                    WHERE swc.product_id IS NOT NULL
                    GROUP BY swc.product_id, sw.company_id
                ),
                base AS (
                    SELECT
                        p.id AS product_id,
                        t.company_id,
                        COALESCE(
                            (p.standard_price->>(t.company_id::text))
                            ::numeric,
                            0.0) AS std_price
                    FROM product_product p
                    JOIN product_template t ON p.product_tmpl_id = t.id
                    WHERE p.active = TRUE
                )
                SELECT
                    b.product_id AS id,
                    b.product_id,
                    b.company_id,
                    COALESCE(wc.wh_cost, 0.0) AS warehouse_cost,
                    b.std_price AS standard_price,
                    -- Effective cost: prefer warehouse cost when it's
                    -- non-zero (i.e., there's on-hand stock); otherwise
                    -- fall back to standard_price.
                    CASE WHEN COALESCE(wc.wh_cost, 0.0) > 0
                         THEN wc.wh_cost
                         WHEN b.std_price > 0
                         THEN b.std_price
                         ELSE 0.0
                    END AS effective_cost,
                    CASE WHEN COALESCE(wc.wh_cost, 0.0) > 0
                         THEN 'warehouse'
                         WHEN b.std_price > 0
                         THEN 'standard'
                         ELSE 'zero'
                    END AS cost_source
                FROM base b
                LEFT JOIN warehouse_cost wc
                       ON wc.product_id = b.product_id
                      AND wc.company_id = b.company_id
            )
        """ % self._table)

    @api.model
    def get_cost(self, product_id, company_id=None):
        """Convenience helper: return the effective cost for one product.

        Used by report_stock_movement.py which assembles values in Python
        rather than SQL.
        """
        company_id = company_id or self.env.company.id
        self.env.cr.execute("""
            SELECT effective_cost FROM product_effective_cost
            WHERE product_id = %s AND company_id = %s
            LIMIT 1
        """, (product_id, company_id))
        row = self.env.cr.fetchone()
        return row[0] if row else 0.0

    @api.model
    def get_moving_avg_cost(self, product_ids, company_id=None):
        """Canonical cost for ALL reports: the product's effective cost.

        Reads ``effective_cost`` from this view (``product_effective_cost``),
        which is the warehouse-weighted average cost with a fall back to
        ``standard_price``. This is the single cost source used across every
        report (inventory value, stock movement, profitability, dashboard
        margin) and carries NO dependency on ``stock_account`` /
        ``stock_valuation_layer`` — so it works whether or not Inventory
        Valuation is installed.

        Returns {product_id: effective_cost}. Products absent from the view
        (e.g. inactive) are simply missing from the dict (caller treats as
        0 / excludes).

        :param product_ids: iterable of product.product ids
        :param company_id: kept for signature compatibility; the view holds
            a single effective cost per product, so it is not used to filter.
        """
        if not product_ids:
            return {}
        self.env.cr.execute("""
            SELECT product_id, effective_cost
              FROM product_effective_cost
             WHERE product_id IN %s
        """, (tuple(product_ids),))
        return {r[0]: (r[1] or 0.0) for r in self.env.cr.fetchall()}

    @api.model
    def get_moving_avg_cost_one(self, product_id, company_id=None):
        """Single-product convenience wrapper for get_moving_avg_cost."""
        return self.get_moving_avg_cost(
            [product_id], company_id).get(product_id, 0.0)
