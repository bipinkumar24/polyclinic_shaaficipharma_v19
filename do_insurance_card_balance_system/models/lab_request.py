from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class LaboratoryRequest(models.Model):
	_inherit = 'acs.laboratory.request'

	available_insurancecard_balance_lab = fields.Boolean('With Insurance Card')
	insurancecard_balance_amount = fields.Float(string="Card Balance")
	insurance_covers_amount = fields.Float('Insurance Covers')
	insurancecard_total_amount = fields.Float('Total Amount', compute='_compute_insurance_bill_payamount', store=True)
	patient_pay_amount = fields.Float('Patient Pay Amount',store=True)
	new_insurance_company_id = fields.Many2one('hms.insurance.company', string="Insurance Company")
	card_insurance_company_id = fields.Many2one('res.partner', related="new_insurance_company_id.partner_id", string="Name")
	insurance_readonly = fields.Boolean(string="Insurance Readonly", compute="_compute_insurance_readonly", store=True)
	show_price = fields.Boolean(compute='_compute_show_price')

	def _compute_show_price(self):
		for rec in self:
			rec.show_price = self.env.user.has_group('acs_hms_pharmacy.group_show_amounts_on_prescription')

	@api.depends('invoice_id.state')
	def _compute_insurance_readonly(self):
		for rec in self:
			rec.insurance_readonly = bool(
				rec.invoice_id and rec.invoice_id.state == 'posted'
			)

	@api.depends('insurancecard_balance_amount', 'insurance_covers_amount', 'total_price')
	def _compute_insurance_bill_payamount(self):
		for rec in self:
			rec.insurancecard_total_amount = rec.total_price
			patient_pay_amount = 0
			patient_pay_amount = rec.insurancecard_total_amount - rec.insurance_covers_amount
			if patient_pay_amount > 0:
				rec.patient_pay_amount = rec.insurancecard_total_amount - rec.insurance_covers_amount
			else:
				rec.patient_pay_amount = 00.0

	@api.onchange('available_insurancecard_balance_lab')
	def get_insurance_company_id(self):
		
		for rec in self:
			if rec.patient_id.new_insurance_company_id:
				rec.new_insurance_company_id = rec.patient_id.new_insurance_company_id.id
				if rec.new_insurance_company_id.partner_id:
					rec.card_insurance_company_id = rec.new_insurance_company_id.partner_id.id

			if rec.available_insurancecard_balance_lab:
					rec.insurance_id = False
					rec.insurance_company_id = False
					rec.claim_id = False
		   
	
	@api.onchange('insurance_id','claim_id')
	def remove_data_balance_lab(self):
		if self.insurance_id or self.claim_id:
			self.available_insurancecard_balance_lab = False



	def create_invoice(self):
		res = super(LaboratoryRequest, self).create_invoice()
		if self.invoice_id and self.available_insurancecard_balance_lab:
			subtotal_amount = sum(line.total_price for line in self.invoice_id.line_ids if not line.display_type)

			insurance_balance = self.patient_pay_amount 
			if subtotal_amount >= insurance_balance:
				patient_amount = min(subtotal_amount, insurance_balance)
			else:
				patient_amount = self.patient_pay_amount

			data = {
                'card_insurance_company_id': self.card_insurance_company_id,
                'available_insurancecard_balance':self.available_insurancecard_balance_lab,
                'patient_amount': patient_amount,
                'acs_object': self,
                'inv_type':'laboratory',
                'rec_field':'request_id',
            }
			insurance_invoice = self.invoice_id.acs_create_insurance_card_invoice(**data)
		return res







