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

    @api.model
    def get_new_partner(self, config_id, domain, offset):
        # v19: POS search / "load more" fetches non-preloaded partners through
        # this backend method (the frontend has no `searchDomain`/`getNewPartners`
        # hook to filter on anymore). Enforce the "hidden customers stay out of
        # POS" rule here so it applies to search & lazy-loading exactly like
        # _load_pos_data_domain does for the initial preload. This leaf ANDs
        # cleanly with the pos_allow_in_pos leaf added by pos_customer_approval_v18.
        domain = list(domain or []) + [('hide_in_pos', '=', False)]
        return super().get_new_partner(config_id, domain, offset)

