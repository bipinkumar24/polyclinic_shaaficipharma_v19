# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import datetime
from odoo.exceptions import UserError, ValidationError


class AdvanceSalaryWizard(models.TransientModel):
    _name = 'loan.installment.wizard'
    _description = "loan Installment wizard"

    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    employee_ids = fields.Many2many('hr.employee', string="Employees")

    def button_generate_partner_ladger(self):
        loan_rule_id = self.env['hr.salary.rule'].search([('code', '=', 'INSTALLMENT')], limit=1)
        debit_account_id = loan_rule_id.account_debit
        date_from = self.date_from
        date_to = self.date_to
        employee_lits = self.employee_ids.ids or False
        line_ids = []
        loan_ids = self.env['loan.installment'].search([('date_from', '>=', date_from), ('date_from', '<=', date_to)])
        employee_ids = self.env['hr.employee'].browse(employee_lits)
        all_move_line_ids = self.env['account.move.line'].search([('date', '>=', date_from),('date', '<=', date_to), ('account_id', '=', debit_account_id.id)])
        if employee_ids:
            partner_ids = employee_ids.mapped('partner_id')
            for partner in partner_ids:
                move_line_ids = all_move_line_ids.filtered(lambda x:x.partner_id.id == partner.id)
                if move_line_ids:
                    line_ids.extend(move_line_ids.ids)
        else:
            employee_ids = self.env['hr.employee'].search([])
            partner_ids = employee_ids.mapped('partner_id')
            for partner in partner_ids:
                move_line_ids = all_move_line_ids.filtered(lambda x:x.partner_id.id == partner.id)
                if move_line_ids:
                    line_ids.extend(move_line_ids.ids)
        return {
            'name': _('Partner Ledger'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'view_id':self.env.ref('account.view_move_line_tree_grouped_partner').id,
            'search_view_id':self.env.ref('account.view_account_move_line_filter').id,
            'domain': [('id', 'in', line_ids)],
            'context': {'search_default_group_by_partner': 1},
        }

class LoanInstallmentTemplete(models.AbstractModel):
    _name = 'report.bi_hr_employee_loan.loan_installment_templete'

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        date_from = data['date_from']
        date_to = data['date_to']
        employee_lits = data['employee_ids']
        data = []
        loan_ids = self.env['loan.installment'].search([('date_from', '>=', date_from), ('date_from', '<=', date_to)])
        employee_ids = self.env['hr.employee'].browse(employee_lits)
        if employee_ids:
            for employee in employee_ids:
                loan_employee_ids = loan_ids.filtered(lambda x:x.employee_id.id == employee.id)
                if loan_employee_ids:
                    data.append({'employee_id': employee, 'lines': loan_employee_ids})
        else:
            employee_ids = self.env['hr.employee'].search([])
            for employee in employee_ids:
                loan_employee_ids = loan_ids.filtered(lambda x:x.employee_id.id == employee.id)
                if loan_employee_ids:
                    data.append({'employee_id': employee, 'lines': loan_employee_ids})
        return {
            'date_from': date_from,
            'docs': docs,
            'data': data
        }
