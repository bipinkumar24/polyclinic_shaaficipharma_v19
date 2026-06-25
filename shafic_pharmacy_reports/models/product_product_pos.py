# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProduct(models.Model):
    """Extend product to expose lot/batch info for the POS expiry popup."""
    _inherit = 'product.product'

    @api.model
    def check_cost_setup(self, product_id):
        """Lightweight cost/unit-mismatch check for the POS backstop.

        Returns a dict {mismatch: bool, message: str}. A mismatch means
        the product's cost is at/above its price, or negative — the
        classic "costed per pack, sold per unit" signature. Non-blocking:
        the POS uses this only to show a notice, never to stop a sale.
        """
        product = self.browse(product_id).exists()
        if not product:
            return {'mismatch': False, 'message': ''}
        param = self.env['ir.config_parameter'].sudo()
        try:
            ratio = float(param.get_param(
                'shafic_pharmacy_reports.cost_warn_ratio', 1.0))
        except (TypeError, ValueError):
            ratio = 1.0
        # Prefer effective (warehouse weighted-avg) cost, fall back to
        # standard price field.
        company_id = self.env.company.id
        cost = self.env['product.effective.cost'].get_cost(
            product_id, company_id) or product.standard_price or 0.0
        price = product.lst_price or product.list_price or 0.0
        if cost < 0:
            return {
                'mismatch': True,
                'message': ('%s has a negative cost — flagged for manager '
                            'review.') % product.display_name,
            }
        if price > 0 and cost >= price * ratio:
            return {
                'mismatch': True,
                'message': ('%s: cost looks higher than price (possible '
                            'pack-vs-unit issue) — flagged for review.')
                           % product.display_name,
            }
        return {'mismatch': False, 'message': ''}

    @api.model
    def get_lots_with_expiry(self, product_id, warehouse_id=None):
        """Return active lots for a product, sorted by expiration ascending.

        Used by the POS expiry-notification popup. Only returns lots that:
          - Belong to the given product
          - Have a positive quantity at the POS's own warehouse
            (so we don't show lots that physically live at another branch
            and can't be dispensed from here)
          - Have an expiration_date set (no point flagging undated lots)

        Args:
            product_id (int): product.product id
            warehouse_id (int|False): stock.warehouse id to scope the
                quant lookup to. When falsy, falls back to all internal
                locations company-wide — the old behavior — so older
                clients that don't pass a warehouse still work.

        Returns:
            dict with:
              count (int): number of distinct lots
              lots (list of dict): each has lot_name, expiration_date,
                                   days_to_expiry, qty_available
              expiry_alert_days (int): the configured warning threshold,
                                       so the JS knows when to auto-popup
        """
        product = self.browse(product_id).exists()
        if not product:
            return {'count': 0, 'lots': [], 'expiry_alert_days': 30}

        # Build the location filter. When a warehouse is provided we
        # only consider quants whose location sits inside that
        # warehouse's location tree, so a lot living at another branch
        # never shows up. When not provided (defensive fallback), we
        # accept any internal location in the company — same as the
        # original behavior.
        location_clause = "loc.usage = 'internal'"
        params = [product_id]
        if warehouse_id:
            warehouse = self.env['stock.warehouse'].browse(
                warehouse_id).exists()
            if warehouse and warehouse.lot_stock_id:
                # parent_path is a hierarchical string like '1/4/12/'.
                # Anything inside the warehouse's root location starts
                # with the root's parent_path, which is the standard
                # way to query Odoo location trees.
                root_path = warehouse.lot_stock_id.parent_path or ''
                if root_path:
                    location_clause += " AND loc.parent_path LIKE %s"
                    params.append(root_path + '%')

        query = """
            SELECT lot.id,
                   lot.name,
                   lot.expiration_date,
                   COALESCE(SUM(q.quantity), 0) AS qty
              FROM stock_lot lot
              JOIN stock_quant q ON q.lot_id = lot.id
              JOIN stock_location loc ON loc.id = q.location_id
             WHERE lot.product_id = %s
               AND {loc_clause}
               AND lot.expiration_date IS NOT NULL
               AND q.quantity > 0
          GROUP BY lot.id, lot.name, lot.expiration_date
            HAVING COALESCE(SUM(q.quantity), 0) > 0
          ORDER BY lot.expiration_date ASC
        """.format(loc_clause=location_clause)
        self.env.cr.execute(query, tuple(params))
        rows = self.env.cr.fetchall()

        today = fields.Date.context_today(self)
        lots = []
        for lot_id, lot_name, expiry, qty in rows:
            days_to_expiry = (expiry - today).days if expiry else None
            lots.append({
                'lot_id': lot_id,
                'lot_name': lot_name or '',
                'expiration_date': expiry.isoformat() if expiry else '',
                'days_to_expiry': days_to_expiry,
                'qty': float(qty),
            })

        alert_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'shafic_pharmacy_reports.expiry_alert_days', 30))

        return {
            'count': len(lots),
            'lots': lots,
            'expiry_alert_days': alert_days,
        }
