# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import dateutil.relativedelta


class Loan_Installment(models.Model):
    _name = 'loan.installment'
    _description = "Loan Installment"
    
    name = fields.Char(string="Name",readonly="True",compute="_compute_name")
    installment_number = fields.Integer(string="Installment Number")
    date_from = fields.Date(string="Date From")
    date_to  = fields.Date(string="Date To")
    principal_amount = fields.Float(string="Principal Amount",digits=(16, 3))
    interest_amount = fields.Float(string="Interest Amount",digits=(32, 2))
    emi_installment = fields.Float(string="EMI(Installment)",digits=(32, 2))
    state = fields.Selection([('unpaid','Unpaid'),('approve','Approved'),('paid','Paid'),('applied_post','Applied For Postpond'),('confirm_postpone','Confirmed Postpone'),('approval_department','Department Approval for Postpond'),('postpone','Postponed')],default='unpaid',string="State")
    employee_id  = fields.Many2one('hr.employee',string="Employee",required=True)
    loan_id = fields.Many2one('loan.request',string="Loan")
    loan_type_id = fields.Many2one('loan.type',string="Loan Type")
    currency_id = fields.Many2one('res.currency',string="Currency")
    interest_acouunting_id = fields.Many2one('account.move',string="Interest Accounting Entry",readonly=True)
    accounting_entry_id = fields.Many2one('account.move',string="Accounting Entry",readonly=True)
    pay_from_payroll = fields.Boolean(string="Payroll")
    installment_booked = fields.Boolean(string="Payroll")
    payable_interest = fields.Boolean(string="Interest payable or not")
    user_id = fields.Many2one('res.users',default=lambda self : self.env.user.id,string="User",readonly=True)
    loan_amount_balance = fields.Float(string="Balance", compute="_compute_loan_amount", store=True)
    skip = fields.Boolean('Skip Installment', copy=True)

    def write(self, vals):
        last_installment_rec = self.env['loan.installment'].search([('loan_id', '=', self.loan_id.id)], limit=1,
                                                                   order='id desc')
        if vals.get('skip'):
            installment_number = 1
            line_ids = self.loan_id.installment_ids.mapped('installment_number')
            if line_ids:
                installment_number = max(line_ids)
            self.copy(default={'date_from': last_installment_rec.date_from + dateutil.relativedelta.relativedelta(months=1),
                               'date_to': last_installment_rec.date_to + dateutil.relativedelta.relativedelta(months=1), 'installment_number': installment_number+1})
        # else:
        #     if not self.env.context.get('is_compute_button'):
        #         last_installment_rec.with_context(is_skip=True).unlink()
        if vals.get('emi_installment'):
            vals['principal_amount'] = vals.get('emi_installment')
        super(Loan_Installment, self).write(vals)

    def unlink(self):
        for rec in self:
            if not self.env.context.get('is_skip'):
                if rec.loan_id:
                    raise UserError(_("You cannot delete Loan !"))
        return super(Loan_Installment, self).unlink()

    @api.depends('employee_id', 'state', 'accounting_entry_id')
    def _compute_loan_amount(self):
        for loan in self:
            if loan.state == 'paid':
                loan.loan_amount_balance = 0
            else:
                loan.loan_amount_balance = loan.emi_installment

    @api.depends('installment_number','loan_id')
    def _compute_name(self):
        for line in self :
            line.name = ""
            if line.loan_id and line.installment_number :
                line.name = line.loan_id.name + '/' + str(line.installment_number)
        return


    def approve_payment(self):
        
        self.write({'state':'approve'})

    def reset_draft(self):

        self.write({'state':'unpaid'})
        
        
    def book_interest(self):
        res = self.env['account.move']

        name_of = self.employee_id.name
        
        debit_line = (0,0,{'account_id' : self.loan_id.employee_account_id.id,
                            'employee_id' : self.employee_id.id,
                            'name' : 'Loan Of ' + name_of,
                            'debit' : self.interest_amount,
                            'credit' : 0.0
                            })


        credit_line = (0,0,{'account_id' : self.loan_id.employee_account_id.id,
                            'employee_id' :self.employee_id.id,
                            'name' : 'Loan Of ' + name_of,
                            'debit' : 0.0,
                            'credit' : self.interest_amount
                            })

        move_line = [debit_line,credit_line]

        jounral = res.create({'date': fields.datetime.now(),
                    'journal_id' :self.loan_id.interest_journal_id.id,
                    'ref' : str(self.installment_number) ,
                    'loan_ids': self.loan_id,
                    'line_ids' : ([debit_line,credit_line])
                    })
        self.write({'interest_acouunting_id' :jounral.id })
        self.installment_booked = True

        return

    def action_payment(self):
        res = self.env['account.move']

        name_of = self.employee_id.name
        
        debit_line = (0,0,{'account_id' : self.loan_id.disburse_journal_id.default_account_id.id,
                            'employee_id' : self.employee_id.id,
                            'name' : 'Loan Of ' + name_of,
                            'debit' : self.emi_installment,
                            'credit' : 0.0
                            })


        credit_line = (0,0,{'account_id' : self.loan_id.employee_account_id.id,
                            'employee_id' : self.employee_id.id,
                            'name' : 'Loan Of ' + name_of,
                            'debit' : 0.0,
                            'credit' : self.emi_installment
                            })

        move_line = [debit_line,credit_line]
        jounral = res.create({'date': fields.datetime.now(),
                    'journal_id' :self.loan_id.disburse_journal_id.id,
                    'ref' : str(self.installment_number) ,
                    'loan_ids': self.loan_id,
                    'line_ids' : ([debit_line,credit_line])
                    })
        self.write({'accounting_entry_id' :jounral.id,'state':'paid' })

        return
  

class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    loan_ids = fields.Many2many('loan.request','rel_move',string = "loan requests")
    is_loan_slip = fields.Boolean()
    
class AccountMoveLineInherit(models.Model):
    _inherit = "account.move.line"

    employee_id = fields.Many2one('hr.employee',string="Employee")
    partner_id = fields.Many2one('res.partner')

class loanImage(models.Model):
    _name = 'loan.image'
    _description = "Document"
    _order = 'sequence, id'

    name = fields.Char("Name", required=True)
    sequence = fields.Integer(default=10, index=True)
    loan_id = fields.Many2one('loan.request', "Loan Request")
    loan_type_ids = fields.Many2many('loan.proof',string="Document Type",required=True)
    document_upload = fields.Binary(string="Document",required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for loan_img in vals_list:
            name = 'Proof'  
            loan_img.update({'name' : name})
        return super(loanImage, self).create(vals_list)        

