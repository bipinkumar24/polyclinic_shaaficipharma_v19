# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeathRegister(models.Model):
    _name = "patient.death.register"
    _description = "Patient Death Register"

    name = fields.Char('Name', readonly=True, copy=False,default='Death')
    date = fields.Datetime(string='Date', required=True, default=fields.Datetime.now)
    date_of_death = fields.Datetime(string='Date of Death', required=True)
    hospitalization_id = fields.Many2one('acs.hospitalization', string='Hospitalization')
    patient_id = fields.Many2one('hms.patient', string="Patient", required=True)
    patient_age = fields.Char(related="patient_id.age", store=True, string="Age")
    patient_gender = fields.Selection(related="patient_id.gender", store=True, string='Gender')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')], string='Status', required=True, readonly=True, copy=False, default='draft')
    physician_id = fields.Many2one('hms.physician', ondelete='restrict', string='Physician', index=True)
    reason = fields.Text (string='Death Reason', required=True)
    extra_info = fields.Text (string='Remarks')
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',default=lambda self: self.env.company) 
    address = fields.Char(string="Patient Address", related="patient_id.partner_id.acs_contact_address_complete", store=True)
    place_of_death = fields.Char(string="Place of Death")
    father_name = fields.Char(string="Father Name")
    mother_name = fields.Char(string="Mother Name")
    marital_status = fields.Selection(related="patient_id.marital_status", string='Marital Status')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                seq_date = None
                if vals.get('date_of_death'):
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_of_death']))
                vals['name'] = self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code('patient.death.register', sequence_date=seq_date) or _("New")
        return super().create(vals_list)

    def unlink(self):
        for data in self:
            if data.state in ['done']:
                raise UserError(('You can not delete record in done state'))
        return super(DeathRegister, self).unlink()

    def action_done(self):
        self.state = 'done'
        self.patient_id.death_register_id = self.id
        self.patient_id.date_of_death = self.date_of_death
        if self.hospitalization_id:
            self.hospitalization_id.death_register_id = self.id
        self.patient_id.active = False

    def action_draft(self):
        self.state = 'draft'

    @api.onchange('hospitalization_id')   
    def onchange_hospitalizaion(self):
        if self.hospitalization_id:
            self.patient_id = self.hospitalization_id.patient_id.id

    @api.onchange('patient_id')   
    def onchange_patient_id(self):
        if self.patient_id:
            self.patient_age = self.patient_id.age


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:   