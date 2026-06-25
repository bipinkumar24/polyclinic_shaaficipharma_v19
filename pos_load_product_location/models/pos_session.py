# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2024 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import api, models


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data.extend(['stock.quant'])
        return data

    def _loader_params_pos_config(self):
        res = super()._loader_params_pos_config()
        fields = res["search_params"]["fields"]
        if "stock_location_id" not in fields:
            fields.append("stock_location_id")

        return res