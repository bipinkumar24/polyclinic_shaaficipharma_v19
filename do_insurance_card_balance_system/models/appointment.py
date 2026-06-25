from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HmsAppointment(models.Model):
    _inherit = 'hms.appointment'
    
    is_invoice = fields.Boolean('Is Invoice')
    available_insurancecard_balance = fields.Boolean('With Insurance Card')
    insurancecard_balance_amount = fields.Float(string="Card Balance")
    insurance_covers_amount = fields.Float('Insurance Covers')
    insurancecard_total_amount = fields.Float('Total Amount', compute='_compute_insurance_bill_payamount', store=True)
    patient_pay_amount = fields.Float('Patient Pay Amount',store=True)
    new_insurance_company_id = fields.Many2one('hms.insurance.company', string="Insurance Company")
    card_insurance_company_id = fields.Many2one('res.partner', related="new_insurance_company_id.partner_id", string="Name")
    insurance_readonly = fields.Boolean(string="Insurance Readonly", compute="_compute_insurance_readonly", store=True)

    @api.onchange('is_charge_the_appoinmnet_fee')
    def _onchange_boolean_chcek(self):
        if not self.is_charge_the_appoinmnet_fee:
            self.is_invoice = False
    @api.depends('invoice_id.state')
    def _compute_insurance_readonly(self):
        for rec in self:
            rec.insurance_readonly = bool(
                rec.invoice_id and rec.invoice_id.state == 'posted'
            )

    def acs_appointment_common_wizard_data(self, invoice_id):
        data = super().acs_appointment_common_wizard_data(invoice_id)
        if not self.invoice_id:
            data += self.procedure_to_invoice_ids.acs_common_invoice_procedure_data(invoice_id)
        req_ids = self.mapped('radiology_request_ids').filtered(lambda req: not req.invoice_id)
        data += req_ids.acs_common_invoice_radiology_data(invoice_id)
        lab_request_ids = self.mapped('lab_request_ids').filtered(lambda req: not req.invoice_id)
        data += lab_request_ids.acs_common_invoice_laboratory_data(invoice_id)
        # prescription_ids = self.mapped('prescription_ids').filtered(lambda req: req.state=='prescription' and not req.invoice_id)
        # data += prescription_ids.acs_common_invoice_prescription_data(invoice_id)
        surgery_ids = self.sudo().surgery_ids.filtered(lambda s: not s.invoice_id)
        data += surgery_ids.acs_common_invoice_surgery_data(invoice_id)
        vaccination_ids = self.mapped('vaccination_ids').filtered(lambda req: not req.invoice_id)
        if vaccination_ids:
            data += [{
                'name': _("Vaccination Charges"),
            }]
            data += vaccination_ids.acs_common_invoice_vaccination_data(invoice_id)


        return data

    @api.depends('available_insurancecard_balance', 'insurance_covers_amount')
    def _compute_insurance_bill_payamount(self):
        for rec in self:
            total_amount = 0.0
            acs_pricelist_id = rec.env.context.get('acs_pricelist_id')

            product_data = rec.acs_appointment_inv_product_data()

            for line in product_data:
                quantity = line.get('quantity', 1)
                uom_id = line.get('product_uom_id')

                # Safely get price
                if line.get('price_unit') is not None:
                    price = line.get('price_unit')
                else:
                    product = line.get('product_id')
                    if not product:
                        continue  # 🔥 skip lines without product

                    price = product.with_context(
                        acs_pricelist_id=acs_pricelist_id
                    )._acs_get_partner_price(
                        quantity,
                        uom_id,
                        rec.patient_id.partner_id
                    )
                if price:
                    total_amount += quantity * price

            rec.insurancecard_total_amount = total_amount
            rec.patient_pay_amount = max(
                total_amount - rec.insurance_covers_amount,
                0.0
            )

    @api.onchange('available_insurancecard_balance', 'insurance_covers_amount')
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
            if rec.available_insurancecard_balance:
                rec.insurance_id = False
                rec.insurance_company_id = False
                rec.claim_id = False

    @api.onchange('insurance_id', 'claim_id')
    def remove_data_available_insurancecard_balance(self):
        if self.insurance_id or self.claim_id:
            self.available_insurancecard_balance = False

    def create_invoice(self):
        res = super(HmsAppointment, self).create_invoice()
        if self.invoice_id and self.available_insurancecard_balance:
            subtotal_amount = sum(line.price_subtotal for line in self.invoice_id.invoice_line_ids if not line.display_type)

            insurance_balance = self.patient_pay_amount
            if subtotal_amount >= insurance_balance:
                patient_amount = min(subtotal_amount, insurance_balance)
            else:
                patient_amount = self.patient_pay_amount
            data = {
                'card_insurance_company_id': self.card_insurance_company_id,
                'available_insurancecard_balance': self.available_insurancecard_balance,
                'patient_amount': patient_amount,
                'acs_object': self,
                'inv_type': 'appointment',
                'rec_field': 'appointment_id',
            }
            insurance_invoice = self.invoice_id.acs_create_insurance_card_invoice(**data)
        return res