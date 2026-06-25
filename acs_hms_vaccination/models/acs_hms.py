#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ACSProduct(models.Model):
    _inherit = 'product.template'

    hospital_product_type = fields.Selection(selection_add=[('vaccination','Vaccination')])
    age_for_vaccine = fields.Char("Age for Vaccine")
    vaccine_dose_number = fields.Integer("Dose")


class ACSPatient(models.Model):
    _inherit = 'hms.patient'

    def _rec_count(self):
        rec = super(ACSPatient, self)._rec_count()
        for rec in self:
            rec.vaccination_count = len(rec.vaccination_ids)

    vaccination_ids = fields.One2many('acs.vaccination', 'patient_id', 'Vaccination')
    vaccination_count = fields.Integer(compute='_rec_count', string='# Vaccination')

    def action_view_vaccinations(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_vaccination.action_vaccination_vac")
        action['domain'] = [('id', 'in', self.vaccination_ids.ids)]
        action['context'] = {'default_patient_id': self.id}
        return action


class Appointment(models.Model):
    _inherit = 'hms.appointment'

    def _vaccination_count(self):
        for rec in self:
            rec.vaccination_count = len(rec.vaccination_ids)

    vaccination_ids = fields.One2many('acs.vaccination', 'appointment_id', 'Vaccination')
    vaccination_count = fields.Integer(compute='_vaccination_count', string='# Vaccination')

    def action_view_vaccinations(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_vaccination.action_vaccination_vac")
        action['domain'] = [('id', 'in', self.vaccination_ids.ids)]
        action['context'] = {'default_appointment_id': self.id, 'default_patient_id': self.patient_id.id}
        return action

    #Method to collect common invoice related records data
    def acs_appointment_common_data(self, invoice_id):
        data = super().acs_appointment_common_data(invoice_id)
        vaccination_ids = self.mapped('vaccination_ids').filtered(lambda req: not req.invoice_id)
        if vaccination_ids:
            data += [{
                'name': _("Vaccination Charges"),
            }]
            data += vaccination_ids.acs_common_invoice_vaccination_data(invoice_id)
        for vaccination in vaccination_ids:
            vaccination.write({'invoice_id': invoice_id.id})
        return data
    
    # MKA: If there are vaccination used as part of a service, they will be considered as a paid service and included in the invoice.
    def get_acs_show_create_invoice(self):
        super().get_acs_show_create_invoice()
        for rec in self:
            if rec.vaccination_ids and not rec.acs_show_create_invoice:
                rec.acs_show_create_invoice = True

class StockMove(models.Model):
    _inherit = "stock.move"

    vaccination_id = fields.Many2one('acs.vaccination', string="Vaccination", ondelete="restrict")


class AccountMove(models.Model):
    _inherit = 'account.move'

    vaccination_id = fields.Many2one('acs.vaccination', string='Vaccination')
    hospital_invoice_type = fields.Selection(selection_add=[('vaccination', 'Vaccination')])

    def acs_update_record_state(self):
        super().acs_update_record_state()
        records = self.env['acs.vaccination'].search([('invoice_id', 'in', self.ids),('state','=','to_invoice')])
        if records:
            records.state = 'done'