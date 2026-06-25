# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import datetime


class Hr_Employee(models.Model):
	_inherit = 'hr.employee'
   
	loan_ids = fields.One2many('loan.request','employee_id')
	policy_ids = fields.Many2many('loan.policies','rel_hr_employee_policies_id',string="Employees")
	allow_multiple_loan = fields.Boolean(string="Allow Multiple Loans")
	partner_id = fields.Many2one('res.partner', string="Partner")
	disburse_journal_id = fields.Many2one('account.journal',string="Disbure Journal",domain="[('type', 'in', ('bank', 'cash','sale','purchase'))]")
	employee_account_id = fields.Many2one('account.account',string="Employee Account")  


	def get_installment_loan(self,id,date_from,date_to) :
		installment_rec = self.env['loan.installment'].sudo().search([('employee_id','=',id),('date_from','=',date_from),
																	('date_to','=',date_to),('state','=','unpaid'),
																	('skip', '=', False)])
		
		amount =0.0
		for rec in installment_rec:
			loan = self.env['loan.request'].sudo().search([('id','=',rec.loan_id.id)])
			if loan.loan_type_id.disburse_method == 'direct':
				pass
			else :
				amount += rec.principal_amount
		return amount 
			   
	def get_interest_loan(self,id,date_from,date_to) :
		installment_rec = self.env['loan.installment'].sudo().search([('employee_id','=',id),('date_from','>=',date_from),
																	('date_to','<=',date_to),('state','=','unpaid')])
		interest = 0.0
		for rec in installment_rec:
			if rec.pay_from_payroll == True :
				pass
			else :
				interest+=rec.interest_amount
		return interest  

class EmployeePublic(models.Model):
	_inherit = 'hr.employee.public'

	loan_ids = fields.One2many('loan.request','employee_id')
	policy_ids = fields.Many2many('loan.policies','rel_hr_employee_policies_id',string="Employees")
	allow_multiple_loan = fields.Boolean(string="Allow Multiple Loans")
	
class Hr_paysleep(models.Model):
	_inherit = "hr.payslip"

	def action_payslip_done(self):
		res = super(Hr_paysleep, self).action_payslip_done()
		self._action_create_account_move()
		for payslip in self:
			payslip.compute_sheet()
			installment_rec = self.env['loan.installment'].sudo().search([('employee_id','=',payslip.employee_id.id),('date_from','=',payslip.date_from),
																		('date_to','=',payslip.date_to)],order="id desc")
			if installment_rec :
				for rec in installment_rec:
					loan = self.env['loan.request'].sudo().search([('id','=',rec.loan_id.id)])
					if loan.loan_type_id.disburse_method == 'payroll':
						if rec.state not in ['paid','postpone']:
							rec.state = 'paid'
							# payslip.move_id.write({'line_ids' : move_line})
							payslip.write({'state': 'done'})
							loans = self.env['loan.request'].search([('employee_id','=',rec.employee_id.id)])
							accounting_entry_id = payslip.move_id.id if payslip.move_id else False
							rec.update({'state':'paid', 'accounting_entry_id': payslip.move_id.id})
							for record in loans:
								if payslip.move_id:
									record.write({'move_entries': [(4, payslip.move_id.id)]})
						else:
							pass
					else:
						pass
