from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class RadiologyRequest(models.Model):
	_inherit = 'acs.radiology.request'

	available_insurancecard_balance_1 = fields.Boolean('With Insurance Card')
	insurancecard_balance_amount = fields.Float(string="Card Balance")
	insurance_covers_amount = fields.Float('Insurance Covers')
	insurancecard_total_amount = fields.Float('Total Amount', store=True)
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

	@api.onchange('available_insurancecard_balance_1','insurancecard_balance_amount', 'insurance_covers_amount', 'total_price')
	def get_insurance_company_id(self):
		self.insurancecard_total_amount = self.total_price
		patient_pay_amount = 0
		patient_pay_amount = self.insurancecard_total_amount - self.insurance_covers_amount
		if patient_pay_amount < 0:
			self.patient_pay_amount = 00.0
		else:
			self.patient_pay_amount = self.insurancecard_total_amount - self.insurance_covers_amount

		
		for rec in self:
			if rec.patient_id.new_insurance_company_id:
				rec.new_insurance_company_id = rec.patient_id.new_insurance_company_id.id
				if rec.new_insurance_company_id.partner_id:
					rec.card_insurance_company_id = rec.new_insurance_company_id.partner_id.id

			# if rec.insurance_covers_amount > rec.insurancecard_balance_amount:
			# 	raise ValidationError(
			# 		_("Spend Amount cannot be greater than Insurance Card Balance Amount.")
			# 	)


	def create_invoice(self):
		res = super(RadiologyRequest, self).create_invoice()
		if self.invoice_id and self.available_insurancecard_balance_1:
			subtotal_amount = sum(line.total_price for line in self.invoice_id.line_ids if not line.display_type)

			insurance_balance = self.patient_pay_amount 
			if subtotal_amount >= insurance_balance:
				patient_amount = min(subtotal_amount, insurance_balance)
			else:
				patient_amount = self.patient_pay_amount
			data = {
				'card_insurance_company_id': self.card_insurance_company_id,
				'available_insurancecard_balance':self.available_insurancecard_balance_1,
				'patient_amount': patient_amount,
				'acs_object': self,
				'inv_type':'radiology',
				'rec_field':'radiology_request_id',
			}
			insurance_invoice = self.invoice_id.acs_create_insurance_card_invoice(**data)
		return res 