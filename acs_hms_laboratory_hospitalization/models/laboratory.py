# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AcsLaboratoryRequest(models.Model):
    _inherit = 'acs.laboratory.request'

    hospitalization_id = fields.Many2one('acs.hospitalization', string='Hospitalization', ondelete='restrict')

    def prepare_test_result_data(self, line, patient):
        res = super(AcsLaboratoryRequest, self).prepare_test_result_data(line, patient)
        res['hospitalization_id'] = self.hospitalization_id and self.hospitalization_id.id or False
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: