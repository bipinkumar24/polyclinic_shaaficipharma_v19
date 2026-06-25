# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ACSSurgery(models.Model):
    _inherit = 'hms.surgery'

    available_insurancecard_balance_surgery = fields.Boolean('With Insurance Card')
    insurancecard_balance_amount = fields.Float(string="Card Balance")
    insurance_covers_amount = fields.Float('Insurance Covers')
    insurancecard_total_amount = fields.Float('Total Amount', compute='_compute_insurance_bill_payamount', store=True)
    patient_pay_amount = fields.Float('Patient Pay Amount',store=True)
    new_insurance_company_id = fields.Many2one('hms.insurance.company', string="Insurance Company")
    card_insurance_company_id = fields.Many2one('res.partner', related="new_insurance_company_id.partner_id", string="Name")
    insurance_readonly = fields.Boolean(string="Insurance Readonly", compute="_compute_insurance_readonly", store=True)


    @api.depends('invoice_id.state')
    def _compute_insurance_readonly(self):
        for rec in self:
            rec.insurance_readonly = bool(
                rec.invoice_id and rec.invoice_id.state == 'posted'
            )

    @api.depends('surgery_product_id', 'insurance_covers_amount')
    def _compute_insurance_bill_payamount(self):
        for rec in self:
            if rec.surgery_product_id:
                rec.insurancecard_total_amount =  rec.surgery_product_id.lst_price
            patient_pay_amount = rec.insurancecard_total_amount - rec.insurance_covers_amount
            if patient_pay_amount < 0:
                rec.patient_pay_amount = 00.0
            else:
                rec.patient_pay_amount = rec.insurancecard_total_amount - rec.insurance_covers_amount


    @api.onchange('available_insurancecard_balance_surgery','insurancecard_balance_amount', 'insurance_covers_amount')
    def get_insurance_company_id(self):
        for rec in self:
            if rec.patient_id.new_insurance_company_id:
                rec.new_insurance_company_id = rec.patient_id.new_insurance_company_id.id
                if rec.new_insurance_company_id.partner_id:
                    rec.card_insurance_company_id = rec.new_insurance_company_id.partner_id.id

            # if rec.insurance_covers_amount > rec.insurancecard_balance_amount:
            #     raise ValidationError(
            #         _("Spend Amount cannot be greater than Insurance Card Balance Amount.")
            #     )
    
    @api.onchange('insurance_id','claim_id')
    def remove_data_available_insurancecard_balance(self):
        if self.insurance_id or self.claim_id:
            self.available_insurancecard_balance_surgery = False

    def action_create_invoice(self):
        res = super(ACSSurgery, self).action_create_invoice()
        if self.invoice_id and self.available_insurancecard_balance_surgery:
            subtotal_amount = sum(line.price_subtotal for line in self.invoice_id.invoice_line_ids if not line.display_type)

            insurance_balance = self.patient_pay_amount 
            if subtotal_amount >= insurance_balance:
                patient_amount = min(subtotal_amount, insurance_balance)
            else:
                patient_amount = self.patient_pay_amount

            data = {
                'card_insurance_company_id': self.card_insurance_company_id,
                'available_insurancecard_balance':self.available_insurancecard_balance_surgery,
                'patient_amount': patient_amount,
                'acs_object': self,
                'inv_type':'surgery',
                'rec_field':'surgery_id',
            }
            insurance_invoice = self.invoice_id.acs_create_insurance_card_invoice(**data)
        return res 

