# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_card_commission(self):
        return {
            "search_params": {
                "fields": ["name", "card_number"],
            }
        }

    def _load_pos_data_models(self, config_id):
        models = super()._load_pos_data_models(config_id)
        models.append('res.card.commission')
        return models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _pos_ui_models_to_load(self):
        res = super()._pos_ui_models_to_load()
        res.append("res.card.commission")
        return res
