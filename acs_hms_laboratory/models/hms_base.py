# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ACSAppointment(models.Model):
    _inherit='hms.appointment'

    def _rec_count(self):
        for rec in self:
            rec.request_count = len(rec.lab_request_ids)
            rec.test_count = len(rec.test_ids)

    def _acs_get_attachments(self):
        attachments = super(ACSAppointment, self)._acs_get_attachments()
        attachments += self.test_ids.mapped('attachment_ids')
        return attachments

    test_ids = fields.One2many('patient.laboratory.test', 'appointment_id', string='Lab Tests')
    lab_request_ids = fields.One2many('acs.laboratory.request', 'appointment_id', string='Lab Requests')
    request_count = fields.Integer(compute='_rec_count', string='# Lab Requests')
    test_count = fields.Integer(compute='_rec_count', string='# Lab Tests')

    def action_lab_request(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_laboratory.hms_action_lab_test_request")
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_physician_id': self.physician_id.id, 'default_appointment_id': self.id}
        action['views'] = [(self.env.ref('acs_laboratory.patient_laboratory_test_request_form').id, 'form')]
        return action

    def action_view_test_results(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_laboratory.action_lab_result")
        action['domain'] = [('id','in',self.test_ids.ids)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_physician_id': self.physician_id.id, 'default_appointment_id': self.id}
        return action

    def action_view_lab_request(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_laboratory.hms_action_lab_test_request")
        action['domain'] = [('id','in',self.lab_request_ids.ids)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_physician_id': self.physician_id.id, 'default_appointment_id': self.id}
        return action

    #Method to collect common invoice related records data
    def acs_appointment_common_data(self, invoice_id):
        data = super().acs_appointment_common_data(invoice_id)
        lab_request_ids = self.mapped('lab_request_ids').filtered(lambda req: not req.invoice_id)
        data += lab_request_ids.acs_common_invoice_laboratory_data(invoice_id)
        # append lab requests in invoice many2many
        if lab_request_ids:
            invoice_id.write({
                'lab_request_move_ids': [(4, req.id) for req in lab_request_ids]
            })
            for lab in lab_request_ids:
                lab.write({'invoice_id': invoice_id.id})
        return data
    
    # MKA: If there are laboratory test used as part of a service, they will be considered as a paid service and included in the invoice.
    def get_acs_show_create_invoice(self):
        super().get_acs_show_create_invoice()
        for rec in self:
            if rec.lab_request_ids and not rec.acs_show_create_invoice and any(lab.acs_show_create_invoice for lab in rec.lab_request_ids):
                rec.acs_show_create_invoice = True

class Treatment(models.Model):
    _inherit = "hms.treatment"

    def _lab_rec_count(self):
        for rec in self:
            rec.request_count = len(rec.request_ids)
            rec.test_count = len(rec.test_ids)

    request_ids = fields.One2many('acs.laboratory.request', 'treatment_id', string='Lab Requests')
    test_ids = fields.One2many('patient.laboratory.test', 'treatment_id', string='Tests')
    request_count = fields.Integer(compute='_lab_rec_count', string='# Lab Requests')
    test_count = fields.Integer(compute='_lab_rec_count', string='# Lab Tests')

    def action_lab_request(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_laboratory.hms_action_lab_test_request")
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_treatment_id': self.id}
        action['views'] = [(self.env.ref('acs_laboratory.patient_laboratory_test_request_form').id, 'form')]
        return action

    def action_lab_requests(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_laboratory.hms_action_lab_test_request")
        action['domain'] = [('id','in',self.request_ids.ids)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_treatment_id': self.id}
        return action

    def action_view_test_results(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_laboratory.action_lab_result")
        action['domain'] = [('id','in',self.test_ids.ids)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_treatment_id': self.id}
        return action

class AccountMove(models.Model):
    _inherit = "account.move"

    lab_request_move_ids = fields.Many2many(
        "acs.laboratory.request",
        "account_move_lab_request_rel",  # relation table
        "move_id",
        "lab_request_id",
        string="Lab Requests"
    )

    def action_post(self):
        res = super().action_post()

        for move in self:
            lab_requests = move.lab_request_move_ids.filtered(lambda r: r.state == 'requested')
            if lab_requests:
                lab_requests.button_accept()

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: