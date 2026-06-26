# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class StockLocation(models.Model):
    _inherit = ['stock.location', 'pos.load.mixin']
    _name = 'stock.location'

    @api.model
    def _load_pos_data_domain(self, data, config):
        # Only load locations that are configured in the POS
        location_ids = config.stock_location_ids
        if location_ids:
            return [('id', 'child_of', location_ids.ids)]
        return [('id', '=', False)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'complete_name']


class StockQuant(models.Model):
    _inherit = ['stock.quant', 'pos.load.mixin']
    _name = 'stock.quant'

    @api.model
    def _load_pos_data_domain(self, data, config):
        """
        Load ONLY quants from the configured stock_location_ids (and their children).
        This is the single source of truth for available qty per location.
        The JS side (pos_store.js) sums these to compute product.qty_available.
        """
        location_ids = config.stock_location_ids
        if location_ids:
            _logger.info(
                "[ts_pos] Loading quants for POS config '%s', locations: %s",
                config.name,
                location_ids.mapped('complete_name'),
            )
            return [
                ('location_id', 'child_of', location_ids.ids),
                ('quantity', '>', 0),
            ]
        _logger.warning(
            "[ts_pos] POS config '%s' has no stock_location_ids – no quants will be loaded",
            config.name,
        )
        return [('id', '=', False)]  # empty result set

    @api.model
    def _load_pos_data_fields(self, config):
        return ['product_id', 'location_id', 'quantity', 'lot_id', 'package_id']
