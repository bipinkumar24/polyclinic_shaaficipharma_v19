# -*- coding: utf-8 -*-

from odoo import models, api


class StockLocation(models.Model):
    _inherit = ['stock.location', 'pos.load.mixin']
    _name = 'stock.location'

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name', 'id', 'complete_name']


class StockQuant(models.Model):
    _inherit = ['stock.quant', 'pos.load.mixin']
    _name = 'stock.quant'

    @api.model
    def _load_pos_data_domain(self, data, config_id):
        """Load quants only for the configured stock location (and its children)."""
        if config_id.stock_location_id:
            return [
                ('location_id', 'child_of', config_id.stock_location_id.id),
                ('quantity', '>', 0),
            ]
        return []

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['product_id', 'location_id', 'quantity', 'lot_id', 'package_id']