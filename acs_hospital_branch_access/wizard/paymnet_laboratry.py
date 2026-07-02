from odoo import models, fields, api


class AccountPaymentRegisterLaboratry(models.TransientModel):
    _name = 'account.payment.laboratry'
    _description = 'Payment Registration Wizard'

    lab_request = fields.Boolean('Lab lab request')
    lab_request_id = fields.Many2one('acs.laboratory.request', string="Lab Request")
    radiology_request = fields.Boolean('radiology request')
    radiology_request_id = fields.Many2one('acs.radiology.request', string="Radiology Request")
    produre_id = fields.Many2one('acs.patient.procedure', string="Procedure")
    is_procedure = fields.Boolean(string="is procedure")
    prescription_id = fields.Many2one('prescription.order', string="prescription")
    is_prescription = fields.Boolean(string="is Prescription")
    suregery_id = fields.Many2one('hms.surgery', string="Surgery")
    is_surgery = fields.Boolean(string="is Surgery")
    partner_id = fields.Many2one('res.partner', string='Partner')
    journal_id = fields.Many2one('account.journal', string='Journal', default=lambda self: self._get_default_journal(), domain="['|',('type', '=', 'bank'),('type', '=', 'cash')]")
    payment_amount = fields.Float(string='Payment Amount')
    payment_date = fields.Date(string='Payment Date', default=fields.Date.today())

    def _get_default_journal(self):
        default_journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        return default_journal.id if default_journal else False

    def set_default_values_lab_request(self, order):
        self.partner_id = order.patient_id.partner_id.id
        self.payment_amount = order.total_price
        self.lab_request_id = order.id
        self.lab_request = True

    def set_default_values_radiology_request(self, order):
        self.partner_id = order.patient_id.partner_id.id
        self.payment_amount = order.total_price
        self.radiology_request_id = order.id
        self.radiology_request = True

    def set_default_values_procedure_request(self, order):
        self.partner_id = order.patient_id.partner_id.id
        self.payment_amount = order.price_unit
        self.produre_id = order.id
        self.is_procedure = True

    def set_default_values_prescription_request(self, order):
        self.partner_id = order.patient_id.partner_id.id
        self.payment_amount = order.amount_total
        self.prescription_id = order.id
        self.is_prescription = True

    def set_default_values_surgery_request(self, order):
        self.partner_id = order.patient_id.partner_id.id
        self.payment_amount = order.invoice_id.amount_total
        self.suregery_id = order.id
        self.is_surgery = True

    def register_a_payment(self):
        payment_vals = {
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
            'amount': self.payment_amount,
            'date': self.payment_date,
        }
        payment = self.env['account.payment'].create(payment_vals)
        if self.lab_request_id:
            self.lab_request_id.laboratory_payment_id = payment.id
            self.lab_request_id.state = 'accepted'
        if self.radiology_request_id:
            self.radiology_request_id.radiology_payment_id = payment.id
            self.radiology_request_id.state = 'accepted'
        if self.produre_id:
            self.produre_id.procedure_payment_id = payment.id
            self.produre_id.state = 'accepted'
        if self.prescription_id:
            self.prescription_id.procedure_payment_id = payment.id
            self.prescription_id.state = 'accepted'
        if self.suregery_id:
            self.suregery_id.surgery_payment_id = payment.id
            self.suregery_id.state = 'accepted'
        return payment
