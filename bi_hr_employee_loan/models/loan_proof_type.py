# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import datetime


class Loan_Proof(models.Model):
	_name = 'loan.proof'
	_description = "Loan Proof"

	name = fields.Char(string="Name")
	mandatory = fields.Boolean(string='Mandatory')


class Loan_Type(models.Model):
	_name = 'loan.type'
	_description = "Loan Type"	

	name = fields.Char(string="Name",required=True)
	code = fields.Char(string="Code")
	is_interest_payable = fields.Boolean(string="Is Interest Payable",default=True)
	interest_mode = fields.Selection([('flat','Flat'),('reducing','Reducing')],string="Interest Mode")
	disburse_method = fields.Selection([('payroll','Deduction From Payroll'),('direct','Direct Cash/Cheque')],default="direct",string="Disburse Method")
	company_id = fields.Many2one('res.company' ,default=lambda self: self.env.company,string="Company",readonly=True)
	rate = fields.Float(string="Rate")

	loan_proof_ids = fields.Many2many('loan.proof','rel_loan_proof_type_id',string="Loan Proofs")
	employee_category_ids = fields.Many2many('hr.employee.category','rel_hr_employee_category_id',string="Employee Category")
	employee_ids = fields.Many2many('hr.employee','rel_hr_employee_loan_type_id',string="Employees")
	loan_ids = fields.Many2many('loan.request' , string = "Loan request" , compute="_fetch_loan_type_request")

	done_loan_count = fields.Integer(string="done loan" ,compute = "_fetch_done_loan_count")
	cancel_loan_count = fields.Integer(string="cancel loan" ,compute = "_fetch_cancel_loan_count")
	applied_loan_count = fields.Integer(string="applied loan" ,compute = "_fetch_applied_loan_count")
	disbursed_loan_count = fields.Integer(string = "disbursed Loan" ,compute = "_fetch_disbursed_loan_count")
	account_loan_count = fields.Integer(string = "accountant Loan" ,compute = "_fetch_accountant_loan_count")
	hide_interest = fields.Boolean()

	@api.onchange('employee_category_ids')
	def _onchange_employee_category(self):
		if not self.employee_category_ids:
			return {'domain': {'employee_ids': [(1,'=',1)]}}

		if self.employee_category_ids:
			return {'domain': {'employee_ids': [('category_ids','in',self.employee_category_ids.ids)]}}
	
	@api.onchange('is_interest_payable')
	def hide_fields(self):
		if self.is_interest_payable == True:
			self.update({'hide_interest': False})
		else:
			self.update({'hide_interest': True})

	@api.model
	def _fetch_disbursed_loan_count(self):
		for type_id in self:
			loan_id = self.env['loan.request'].search([('loan_type_id','=', type_id.id),('stage','=','disbursed')])
			if loan_id:
				type_id.disbursed_loan_count = len(loan_id)
			else:
				type_id.disbursed_loan_count = 0

	@api.model
	def _fetch_accountant_loan_count(self):
		for type_id in self:
			loan_id = self.env['loan.request'].search([('loan_type_id','=', type_id.id),('stage','=','waiting')])
			if loan_id:
				type_id.account_loan_count = len(loan_id)
			else:
				type_id.account_loan_count = 0


	@api.model
	def _fetch_done_loan_count(self):
		for type_id in self:
			loan_id = self.env['loan.request'].search([('loan_type_id','=', type_id.id),('stage','=','approve')])
			if loan_id:
				type_id.done_loan_count = len(loan_id)
			else:
				type_id.done_loan_count = 0

	@api.model
	def _fetch_cancel_loan_count(self):
		for type_id in self:
			loan_id = self.env['loan.request'].search([('loan_type_id','=', type_id.id),('stage','=','cancel')])
			if loan_id:
				type_id.cancel_loan_count = len(loan_id)
			else:
				type_id.cancel_loan_count = 0

	@api.model
	def _fetch_applied_loan_count(self):
		for type_id in self:
			loan_id = self.env['loan.request'].search([('loan_type_id','=', type_id.id),('stage','in',['applied','waiting_depart','waiting'])])
			if loan_id:
				type_id.applied_loan_count = len(loan_id)
			else:
				type_id.applied_loan_count = 0								



	@api.model
	def _fetch_loan_type_request(self):
		
		for type_id in self:
			loan_id = self.env['loan.request'].search([('loan_type_id','=', type_id.id)])
			if loan_id:
				type_id.loan_ids = loan_id.ids
			else:
				type_id.loan_ids = []			



	_sql_constraints = [
			('name_uniq', 'unique (code)', _('The code must be unique !')),
		]



class Loan_Policies(models.Model):
	_name = 'loan.policies'
	_description = "Loan Policies"

	name = fields.Char(string="Name",required=True)
	code = fields.Char(string="Code")

	company_id = fields.Many2one('res.company' ,default=lambda self: self.env.company,string="Company",readonly=True)
	policy_type = fields.Selection([('max','Max Loan Amount'),('gap','Gap Between Two Loans'),('qualifying','Qualifying Period')],string="Policy Type")
	basis = fields.Selection([('fix','Fix Amount')],string='Basis')
	values = fields.Float(string="Values")
	duration_months = fields.Integer(string="Duration(Months)")
	days = fields.Integer(string="Days",default=90)
	employee_category_ids = fields.Many2many('hr.employee.category','rel_hr_employee_category_policies',string="Employee Category")
	employee_ids = fields.Many2many('hr.employee','rel_hr_employee_policies_id',string="Employees")
	_sql_constraints = [
			('name_uniq', 'unique (code)', _('The code must be unique !')),
		]

	@api.onchange('employee_category_ids')
	def _onchange_employee_category(self):
		if not self.employee_category_ids:
			return {'domain': {'employee_ids': [(1,'=',1)]}}

		if self.employee_category_ids:
			return {'domain': {'employee_ids': [('category_ids','in',self.employee_category_ids.ids)]}}	

	
	