# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_config(self):
        res = super()._loader_params_pos_config()
        fields = res['search_params']['fields']
        if 'is_restrict_negative' not in fields:
            fields.append('is_restrict_negative')
        if 'stock_location_ids' not in fields:
            fields.append('stock_location_ids')
        return res

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        if 'stock.quant' not in data:
            data.append('stock.quant')
        if 'stock.location' not in data:
            data.append('stock.location')
        return data
