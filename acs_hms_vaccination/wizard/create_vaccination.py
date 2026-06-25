# -*- encoding: utf-8 -*-
from odoo import models, fields, api,_
from datetime import date, datetime, timedelta as td
from odoo.exceptions import UserError

class AcsCreateVaccinations(models.TransientModel):
    _name = "acs.plan.vaccinations"
    _description = "Transfer Accommodation"

    patient_id = fields.Many2one ('hms.patient','Patient', required=True)
    vaccination_on_birthday = fields.Boolean('Schedule on birthday')
    vaccination_group_id = fields.Many2one('vaccination.group',string='Vaccination Group', ondelete="restrict")
    appointment_id = fields.Many2one('hms.appointment', 'Appointment')

    @api.model
    def default_get(self,fields):
        context = self.env.context or {}
        res = super(AcsCreateVaccinations, self).default_get(fields)
        if context.get('active_model') == 'hms.appointment' and context.get('active_ids'):
            appointment = self.env['hms.appointment'].browse(context.get('active_ids', []))
            res.update({
                'patient_id': appointment.patient_id.id,
                'appointment_id': appointment.id,
            })
        elif context.get('active_model') == 'hms.patient' and context.get('active_ids'):
            patient = self.env['hms.patient'].browse(context.get('active_ids', []))
            res.update({
                'patient_id': patient.id,
            })
        return res
    
    def acs_get_vaccination_data(self, line, base_date):
        data = {
            'product_id': line.product_id.id,
            'patient_id': self.patient_id.id, 
            'due_date': (base_date+ td(days=line.date_due_day)),
            'state': 'scheduled',
        }
        if self.appointment_id:
            data['appointment_id'] = self.appointment_id.id
        return data

    def create_vaccinations(self):
        Vaccination = self.env['acs.vaccination']
        base_date = fields.Date.from_string(fields.Date.today())
        if self.vaccination_on_birthday:
            if not self.patient_id.birthday:
                raise UserError(_('Please set Date Of Birth first.'))
            base_date = fields.Date.from_string(self.patient_id.birthday)

        for line in self.vaccination_group_id.group_line_ids:
            data = self.acs_get_vaccination_data(line, base_date)
            Vaccination.create(data)
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
