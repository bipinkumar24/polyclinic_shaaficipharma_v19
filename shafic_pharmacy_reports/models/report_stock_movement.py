# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models, tools


class ReportPharmacyStockMovement(models.Model):
    """Fast / Slow / Dead stock classification and batch tracking.

    This is a stored model refreshed by a scheduled job rather than a
    pure SQL view, because the moving classification depends on
    configurable thresholds.
    """
    _name = 'report.pharmacy.stock.movement'
    _description = 'Pharmacy Stock Movement Analysis'
    _order = 'last_sale_date desc'

    product_id = fields.Many2one('product.product', string='Product',
                                 required=True, index=True)
    categ_id = fields.Many2one('product.category', string='Category')
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category',
        related='product_id.pharmacy_category_id', store=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    qty_on_hand = fields.Float(string='Qty On Hand')
    qty_sold_period = fields.Float(string='Qty Sold (analysis window)')
    last_sale_date = fields.Datetime(string='Last Sale Date')
    days_since_sale = fields.Integer(string='Days Since Last Sale')
    oldest_stock_date = fields.Date(
        string='Oldest Stock Date',
        help='Earliest in_date across all internal-location quants for '
             'this product. Tells you when the oldest unit currently on '
             'the shelf first arrived.')
    days_on_hand = fields.Integer(
        string='Days On Hand',
        help='How long the oldest unit of this product has been sitting '
             'on the shelf. Drives the dead-stock classification: this '
             'is what counts as "old," not when the product last sold.')
    movement_class = fields.Selection(
        selection=[
            ('fast', 'Fast Moving'),
            ('slow', 'Slow Moving'),
            ('dead', 'Dead Stock'),
        ], string='Movement Class (Age)',
        help='How long the oldest unit on the shelf has been sitting. '
             'Fast = under 60 days; Slow = 60-180 days; Dead = over '
             '180 days. Configurable in Settings.')
    days_of_cover = fields.Float(
        string='Days of Cover', digits=(10, 1),
        help='At the current sales rate, how many days the on-hand '
             'quantity would last. Calculated as: qty_on_hand / '
             '(qty_sold_period / sales_window_days). High values mean '
             'stock is moving slowly relative to what is on hand. A '
             'product with 100 units on hand selling 2 per 180 days '
             'has 9,000 days of cover.')
    velocity_class = fields.Selection(
        selection=[
            ('fast', 'Fast Velocity'),
            ('slow', 'Slow Velocity'),
            ('dead', 'Dead Velocity'),
        ], string='Velocity Class',
        help='Independent of age. Catches products where the ratio of '
             'sold quantity to on-hand quantity is too low, even if the '
             'stock itself is recent. A young product with too much '
             'inventory relative to sales gets flagged here.')
    stock_value = fields.Float(string='Stock Value at Risk')

    @api.model
    def refresh_movement_analysis(self):
        """Recompute the fast/slow/dead classification for all stockable
        products.

        Classification is driven by **stock age** (how long the oldest
        unit of this product has been sitting on the shelf), NOT by
        sales recency. This avoids the common false positive of newly-
        received products being flagged as dead just because they have
        no sales history yet.

        Rule:
          Dead  = oldest unit on shelf older than dead_stock_days (180)
          Slow  = oldest unit older than slow_stock_days (60)
          Fast  = oldest unit newer than slow_stock_days

        Sales history (days_since_sale, last_sale_date, qty_sold) is
        still captured and shown alongside, so a reviewer can see e.g.
        "this product has been on hand 200 days AND hasn't sold in 200
        days" — a much stronger signal than either dimension alone.
        """
        param = self.env['ir.config_parameter'].sudo()
        slow_days = int(param.get_param(
            'shafic_pharmacy_reports.slow_stock_days', 60))
        dead_days = int(param.get_param(
            'shafic_pharmacy_reports.dead_stock_days', 180))
        # Velocity (days-of-cover) thresholds. Independent axis from
        # age — catches young products with too much stock relative to
        # sales rate.
        velocity_slow_cover = float(param.get_param(
            'shafic_pharmacy_reports.velocity_slow_days_of_cover', 90))
        velocity_dead_cover = float(param.get_param(
            'shafic_pharmacy_reports.velocity_dead_days_of_cover', 180))
        today = fields.Date.context_today(self)
        sales_window_start = today - timedelta(days=dead_days)

        self.search([]).unlink()

        products = self.env['product.product'].search([
            ('type', '=', 'consu'),
            ('is_storable', '=', True),
        ]) if 'is_storable' in self.env['product.product']._fields else \
            self.env['product.product'].search([('type', '=', 'product')])

        # POS sales aggregation — informational only, no longer drives
        # classification.
        self.env.cr.execute("""
            SELECT l.product_id,
                   SUM(l.qty) AS qty_sold,
                   MAX(o.date_order) AS last_sale
            FROM pos_order_line l
            JOIN pos_order o ON l.order_id = o.id
            WHERE o.state IN ('paid', 'done', 'invoiced')
              AND o.date_order >= %s
              AND l.qty > 0
            GROUP BY l.product_id
        """, (sales_window_start,))
        sales_map = {r[0]: (r[1], r[2]) for r in self.env.cr.fetchall()}

        # Stock-age aggregation — drives classification. For each
        # product we want the EARLIEST in_date across all positive-
        # quantity internal-location quants. That's the age of the
        # oldest unit currently on the shelf.
        self.env.cr.execute("""
            SELECT q.product_id,
                   MIN(q.in_date) AS oldest_in_date
            FROM stock_quant q
            JOIN stock_location loc ON loc.id = q.location_id
            WHERE loc.usage = 'internal'
              AND q.quantity > 0
              AND q.in_date IS NOT NULL
            GROUP BY q.product_id
        """)
        age_map = {r[0]: r[1] for r in self.env.cr.fetchall()}

        vals_list = []
        for product in products:
            qty_on_hand = product.qty_available
            if qty_on_hand <= 0:
                continue

            # Informational: sales history
            qty_sold, last_sale = sales_map.get(product.id, (0.0, None))
            if last_sale:
                days_since = (today - last_sale.date()).days
            else:
                # No sale in the analysis window. Don't fake a value —
                # leave it at 0 and let the caller / view distinguish
                # via last_sale_date being NULL.
                days_since = 0

            # Drives classification: stock age
            oldest_in_date = age_map.get(product.id)
            if oldest_in_date:
                oldest_date = oldest_in_date.date() \
                    if hasattr(oldest_in_date, 'date') else oldest_in_date
                days_on_hand = (today - oldest_date).days
            else:
                # No in_date on any quant. Could be legacy data, a
                # manual inventory adjustment, or odd edge cases.
                # Don't classify these as dead — leave them as fast so
                # they don't crowd the report. They'll get a real
                # in_date on the next receipt.
                oldest_date = None
                days_on_hand = 0

            if days_on_hand > dead_days:
                movement_class = 'dead'
            elif days_on_hand > slow_days:
                movement_class = 'slow'
            else:
                movement_class = 'fast'

            # Velocity classification: days_of_cover at current rate.
            # Independent from age. Catches the case "100 units on
            # shelf, only 2 sold in 180 days" which the age axis can't
            # catch when the stock itself is recent.
            avg_daily_sales = qty_sold / dead_days if qty_sold > 0 else 0.0
            if avg_daily_sales > 0:
                days_of_cover = qty_on_hand / avg_daily_sales
            else:
                # No sales at all in the window → effectively infinite
                # cover. Cap at a large value to keep the column
                # sortable; the velocity_class still reflects 'dead'.
                days_of_cover = 99999.0

            # Grace period: a product needs at least 14 days on the
            # shelf before we judge its velocity. Less than that and
            # there genuinely hasn't been time for the sales pattern to
            # reveal itself. Beyond 14 days, judge honestly — a product
            # with 100 units that sold 4 in 20 days IS over-stocked,
            # even if its stock is technically recent. (Hard-coded
            # rather than configurable to keep settings minimal.)
            if days_on_hand < 14:
                velocity_class = 'fast'
            elif days_of_cover >= velocity_dead_cover:
                velocity_class = 'dead'
            elif days_of_cover >= velocity_slow_cover:
                velocity_class = 'slow'
            else:
                velocity_class = 'fast'

            company_id = product.company_id.id or self.env.company.id
            avg_cost = self.env['product.effective.cost'] \
                .get_moving_avg_cost_one(product.id, company_id)
            vals_list.append({
                'product_id': product.id,
                'categ_id': product.categ_id.id,
                'company_id': company_id,
                'qty_on_hand': qty_on_hand,
                'qty_sold_period': qty_sold,
                'last_sale_date': last_sale,
                'days_since_sale': days_since,
                'oldest_stock_date': oldest_date,
                'days_on_hand': days_on_hand,
                'movement_class': movement_class,
                'days_of_cover': days_of_cover,
                'velocity_class': velocity_class,
                'stock_value': qty_on_hand * (avg_cost or 0.0),
            })
        if vals_list:
            self.create(vals_list)
        return True


class ReportPharmacyBatchTracking(models.Model):
    """Batch / lot tracking report - purchase to sales traceability."""
    _name = 'report.pharmacy.batch.tracking'
    _description = 'Pharmacy Batch & Lot Tracking Report'
    _auto = False
    _order = 'product_id, lot_name'

    lot_id = fields.Many2one('stock.lot', string='Batch / Lot',
                             readonly=True)
    lot_name = fields.Char(string='Batch ID', readonly=True)
    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    expiration_date = fields.Datetime(string='Expiry Date', readonly=True)
    on_hand_qty = fields.Float(string='Remaining Balance', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    sl.id AS id,
                    sl.id AS lot_id,
                    sl.name AS lot_name,
                    sl.product_id AS product_id,
                    sl.expiration_date AS expiration_date,
                    COALESCE(qty.on_hand, 0.0) AS on_hand_qty,
                    sl.company_id AS company_id
                FROM stock_lot sl
                LEFT JOIN (
                    SELECT q.lot_id, SUM(q.quantity) AS on_hand
                    FROM stock_quant q
                    JOIN stock_location loc ON q.location_id = loc.id
                    WHERE loc.usage = 'internal'
                    GROUP BY q.lot_id
                ) qty ON qty.lot_id = sl.id
            )
        """ % self._table)
