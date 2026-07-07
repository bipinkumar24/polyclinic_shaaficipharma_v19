# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2024 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def sync_from_ui(self, orders):
        """Push real-time, location-based stock availability after every order.

        Core validates the delivery picking in-line during ``_process_order``
        (``pos_order.py:157 _create_order_picking``, unless *Update stock at
        closing*), so by the time ``super()`` returns the on-hand quant of the
        configured POS location has already changed. We recompute the on-hand
        quantity of every affected product.template in each config's configured
        stock location(s) and broadcast it on the POS config bus channel so
        out-of-stock products disappear (and refunds re-show them) without a
        POS reload.
        """
        result = super().sync_from_ui(orders)
        try:
            order_ids = [
                vals["id"]
                for vals in (result or {}).get("pos.order", [])
                if isinstance(vals, dict) and vals.get("id")
            ]
            if order_ids:
                self.browse(order_ids).exists()._plpl_broadcast_location_stock()
        except Exception:  # noqa: BLE001 - never break order sync on a notification
            _logger.exception(
                "pos_load_product_location: real-time stock broadcast failed"
            )
        return result

    def _plpl_broadcast_location_stock(self):
        """Notify each affected POS config with the on-hand quantity (in its
        configured stock location(s)) of every product.template sold on it.

        The notification carries two things:
          * ``available_by_tmpl`` — the per-template on-hand total, used by the
            frontend to hide/show products (this module's product grid filter);
          * ``stock.quant`` — the fresh reads of the affected quants, which the
            frontend feeds into ``connectNewData`` so that ``product.stock_quant_ids``
            is up to date for every consumer (e.g. the on-hand check in
            ``pos_auto_lot_selection`` and the negative-stock guard in
            ``ts_pos_stock_no_negative``) without reloading the POS.
        """
        Product = self.env["product.product"]
        Quant = self.env["stock.quant"]
        for config in self.config_id:
            if not config.stock_location_ids:
                continue
            config_orders = self.filtered(lambda o, c=config: o.config_id == c)
            tmpl_ids = config_orders.lines.product_id.product_tmpl_id.ids
            if not tmpl_ids:
                continue

            location_ids = config.stock_location_ids.ids
            # All variants of the touched templates, so a template is only hidden
            # when *every* variant is out of stock in the configured location(s).
            variants = Product.search([("product_tmpl_id", "in", tmpl_ids)])
            quants = Quant.search([
                ("location_id", "child_of", location_ids),
                ("product_id", "in", variants.ids),
            ])

            qty_by_product = {}
            for quant in quants:
                qty_by_product[quant.product_id.id] = (
                    qty_by_product.get(quant.product_id.id, 0.0) + quant.quantity
                )
            available_by_tmpl = dict.fromkeys(tmpl_ids, 0.0)
            for variant in variants:
                available_by_tmpl[variant.product_tmpl_id.id] += qty_by_product.get(
                    variant.id, 0.0
                )

            config._notify("PLPL_STOCK_UPDATE", {
                "available_by_tmpl": available_by_tmpl,
                "stock.quant": Quant._load_pos_data_read(quants, config),
            })
            _logger.info(
                "pos_load_product_location: PLPL_STOCK_UPDATE config=%s availability=%s",
                config.id,
                available_by_tmpl,
            )
