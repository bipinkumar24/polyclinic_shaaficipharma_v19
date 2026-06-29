# -*- coding: utf-8 -*-

from odoo import fields, models,api


class Resuser(models.Model):
    _inherit = 'res.partner'

    # is_commission = fields.Boolean('Is Card Commission')
    hide_in_pos = fields.Boolean(string="Hide Customer In POS", default=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result.append('hide_in_pos')
        return result


    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = super()._load_pos_data_domain(data, config)
        domain.append(('hide_in_pos', '=', False))
        return domain

