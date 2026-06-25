# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.fields import Domain


class RadiologyRequest(models.Model):
    _inherit = "acs.radiology.request"

    @api.model
    def _search(self, domain, *args, **kwargs):
        if self.env.user.has_group('acs_hms_cashier.group_radiology_user'):
            domain = Domain.AND([domain, [('state', '=', 'requested')]])
        return super()._search(domain, *args, **kwargs)


class LaboratoryRequest(models.Model):
    _inherit = "acs.laboratory.request"

    @api.model
    def _search(self, domain, *args, **kwargs):
        if self.env.user.has_group('acs_hms_cashier.group_laboratory_request'):
            domain = Domain.AND([domain, [('state', '=', 'requested')]])
        return super()._search(domain, *args, **kwargs)
