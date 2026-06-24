# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import uuid


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    radiology_request_id = fields.Many2one('acs.radiology.request', string='Radiology Request', copy=False, ondelete='restrict')
    hospital_invoice_type = fields.Selection(selection_add=[('radiology', 'Radiology')])

    def acs_update_record_state(self):
        super().acs_update_record_state()
        records = self.env['acs.radiology.request'].search([('invoice_id', 'in', self.ids),('state','=','to_invoice')])
        if records:
            records.button_done()

class StockMove(models.Model):
    _inherit = "stock.move"

    radiology_test_id = fields.Many2one('patient.radiology.test', string="Radiology Test", ondelete="restrict")


class ACSConsumableLine(models.Model):
    _inherit = "hms.consumable.line"

    patient_radiology_test_id = fields.Many2one('patient.radiology.test', string="Patient Radiology Test", ondelete="restrict")
    radiology_test_id = fields.Many2one('acs.radiology.test', string="Radiology Test", ondelete="restrict")


class ACSPatient(models.Model):
    _inherit = "hms.patient"

    def _rec_count(self):
        rec = super(ACSPatient, self)._rec_count()
        for rec in self:
            rec.radiology_request_count = len(rec.radiology_request_ids)
            rec.radiology_test_count = len(rec.radiology_test_ids)

    def _acs_get_attachments(self):
        attachments = super(ACSPatient, self)._acs_get_attachments()
        attachments += self.radiology_test_ids.mapped('attachment_ids')
        return attachments

    radiology_request_ids = fields.One2many('acs.radiology.request', 'patient_id', string='Radiology Requests')
    radiology_test_ids = fields.One2many('patient.radiology.test', 'patient_id', string='Radiology Tests')
    radiology_request_count = fields.Integer(compute='_rec_count', string='# Radiology Requests')
    radiology_test_count = fields.Integer(compute='_rec_count', string='# Radiology Tests')

    def action_radiology_requests(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_radiology.hms_action_radiology_request")
        action['domain'] = [('id','in',self.radiology_request_ids.ids)]
        action['context'] = {'default_patient_id': self.id}
        return action

    def action_view_test_results(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_radiology.action_radiology_result")
        action['domain'] = [('id','in',self.radiology_test_ids.ids)]
        action['context'] = {'default_patient_id': self.id}
        return action


class product_template(models.Model):
    _inherit = "product.template"

    hospital_product_type = fields.Selection(selection_add=[('radiology', 'Radiology')])


class Physician(models.Model):
    _inherit = "hms.physician"

    def _acs_rec_radiology_count(self):
        RadiologyRequest = self.env['acs.radiology.request']
        RadiologyResult = self.env['patient.radiology.test']
        for record in self.with_context(active_test=False):
            record.radiology_request_count = RadiologyRequest.search_count([('physician_id', '=', record.id)])
            record.radiology_result_count = RadiologyResult.search_count([('physician_id', '=', record.id)])

    radiology_request_count = fields.Integer(compute='_acs_rec_radiology_count', string='# Radiology Request')
    radiology_result_count = fields.Integer(compute='_acs_rec_radiology_count', string='# Radiology Result')

    def action_radiology_request(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_radiology.hms_action_radiology_request")
        action['domain'] = [('physician_id','=',self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action

    def action_radiology_result(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_radiology.action_radiology_result")
        action['domain'] = [('physician_id','=',self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _acs_portal_ensure_token(self):
        """ Get the current record access token """
        if not self.access_token:
            # we use a `write` to force the cache clearing otherwise `return self.access_token` will return False
            self.sudo().write({'access_token': str(uuid.uuid4())})
        return self.access_token

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: