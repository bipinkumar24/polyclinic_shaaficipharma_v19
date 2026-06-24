# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AcsLaboratoryRequest(models.Model):
    _inherit = 'acs.laboratory.request'
    
    appointment_id = fields.Many2one('hms.appointment', string='Appointment', ondelete='restrict')
    treatment_id = fields.Many2one('hms.treatment', string='Treatment', ondelete='restrict')

    def prepare_test_result_data(self, line, patient):
        res = super(AcsLaboratoryRequest, self).prepare_test_result_data(line, patient)
        res['appointment_id'] = self.appointment_id and self.appointment_id.id or False
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: