# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import uuid


class ACSPrescriptionOrder(models.Model):
    _inherit='prescription.order'

    available_insurancecard_balance_prescription = fields.Boolean('With Insurance Card')
    insurancecard_balance_amount = fields.Float(string="Card Balance")
    insurance_covers_amount = fields.Float('Insurance Covers')
    insurancecard_total_amount = fields.Float('Total Amount', store=True)
    patient_pay_amount = fields.Float('Patient Pay Amount', compute='_compute_insurance_bill_payamount', store=True)
    new_insurance_company_id = fields.Many2one('hms.insurance.company', string="Insurance Company")
    card_insurance_company_id = fields.Many2one('res.partner', related="new_insurance_company_id.partner_id", string="Name")
    insurance_readonly = fields.Boolean(string="Insurance Readonly", compute="_compute_insurance_readonly", store=True)


    @api.depends('invoice_id.state')
    def _compute_insurance_readonly(self):
        for rec in self:
            rec.insurance_readonly = bool(
                rec.invoice_id and rec.invoice_id.state == 'posted'
            )

    @api.depends('insurancecard_balance_amount', 'insurance_covers_amount', 'amount_total')
    def _compute_insurance_bill_payamount(self):
        for rec in self:
            rec.insurancecard_total_amount = rec.amount_total
            patient_pay_amount = 0
            patient_pay_amount = rec.insurancecard_total_amount - rec.insurance_covers_amount
            if patient_pay_amount < 0:
                rec.patient_pay_amount = 00.0
            else:
                rec.patient_pay_amount = rec.insurancecard_total_amount - rec.insurance_covers_amount


    @api.onchange('available_insurancecard_balance_prescription','insurancecard_balance_amount', 'insurance_covers_amount')
    def get_insurance_company_id(self):
        
        for rec in self:
            if rec.patient_id.new_insurance_company_id:
                rec.new_insurance_company_id = rec.patient_id.new_insurance_company_id.id
                if rec.new_insurance_company_id.partner_id:
                    rec.card_insurance_company_id = rec.new_insurance_company_id.partner_id.id

            if rec.available_insurancecard_balance_prescription:
                    rec.insurance_id = False
                    rec.insurance_company_id = False
                    rec.claim_id = False
           
    
    @api.onchange('insurance_id','claim_id')
    def remove_data_balance_prescription(self):
        if self.insurance_id or self.claim_id:
            self.available_insurancecard_balance_prescription = False


    def create_invoice(self):
        res = super(ACSPrescriptionOrder, self).create_invoice()
        if self.invoice_id and self.available_insurancecard_balance_prescription:
            subtotal_amount = sum(line.total_price for line in self.invoice_id.line_ids if not line.display_type)

            insurance_balance = self.patient_pay_amount 
            if subtotal_amount >= insurance_balance:
                patient_amount = min(subtotal_amount, insurance_balance)
            else:
                patient_amount = self.patient_pay_amount

            data = {
                'card_insurance_company_id': self.card_insurance_company_id,
                'available_insurancecard_balance':self.available_insurancecard_balance_prescription,
                'patient_amount': patient_amount,
                'acs_object': self,
                'inv_type':'pharmacy',
                'rec_field':'prescription_id',
            }
            insurance_invoice = self.invoice_id.acs_create_insurance_card_invoice(**data)
        return res


