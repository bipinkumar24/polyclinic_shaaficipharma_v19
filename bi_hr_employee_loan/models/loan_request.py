# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import datetime
import calendar
from dateutil.relativedelta import *
from odoo.exceptions import UserError, ValidationError
import dateutil.relativedelta




class Loan_Request(models.Model):
    _name = 'loan.request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']    
    _order = 'applied_date desc, id desc'
    _description = "Loan Request"

    name = fields.Char(string="Name",readonly=True)
    employee_id = fields.Many2one('hr.employee',string="Employee",required=True)
    partner_id = fields.Many2one('res.partner' ,related = 'employee_id.user_id.partner_id' )
    hr_employee_id = fields.Many2one('hr.employee',string="Hr Head")
    account_employee_id = fields.Many2one('hr.employee',string="Account Head")
    department_employee_id = fields.Many2one('hr.employee',string="Department Head")
    cancel_loan_employee_id = fields.Many2one('hr.employee',string="Cancel loan")
    applied_date = fields.Date(string="Applied Date")
    # loan_type_id = fields.Many2one('loan.type',string="Loan Type",required=True ,domain=lambda self:self._get_emp_domain())
    loan_type_id = fields.Many2one('loan.type',string="Loan Type",required=True )
    approve_date = fields.Date(string="Approve Date")
    disbursement_date = fields.Date(string="Disbursement Date")
    department_id = fields.Many2one('hr.department',string="Department" , related = 'employee_id.department_id')
    company_id = fields.Many2one('res.company' ,default=lambda self: self.env.company,string="Company",required=True)
    user_id = fields.Many2one('res.users',default=lambda self : self.env.user.id,string="User",readonly=True)

    duration_months = fields.Integer(string="Duration(Months)",required=True,default=1)
    principal_amount = fields.Float(string="Principal Amount",required=True,digits=(32, 2))
    is_interest_payable = fields.Boolean(string="Is Interest Payable",default=True,related="loan_type_id.is_interest_payable")
    interest_mode = fields.Selection([('flat','Flat'),('reducing','Reducing')],string="Interest Mode",related="loan_type_id.interest_mode")
    rate = fields.Float(string="Rate",related="loan_type_id.rate")
    total_loan = fields.Float(string="Total Loan",compute="_compute_loan_amounts")
    total_interest = fields.Float(string="Total Interest On Loan",compute="_compute_loan_amounts",digits=(32,2))
    additional_amount = fields.Float(string="Additional Amount Every Month")
    received_from_employee = fields.Float(string="Received From Employee",compute="_compute_balance_on_loan")
    balance_on_loan = fields.Float(string="Balance On Loan",compute="_compute_balance_on_loan")

    loan_proof_ids = fields.Many2many('loan.proof','rel_loan_proof_type_request',string="Loan Proofs",related="loan_type_id.loan_proof_ids")

    disburse_journal_id = fields.Many2one('account.journal',string="Disbure Journal",domain="[('type', 'in', ('bank', 'cash','sale','purchase'))]")
    repayment_board_journal_id = fields.Many2one('account.journal',string="Repayment Board Journal")
    interest_journal_id = fields.Many2one('account.journal',string="Interest Journal")
    account_entery_id = fields.Many2one('account.move',string="Accounting Entry",readonly=True)
    loan_entry_id = fields.Many2one('account.move',string="Bank Entry", readonly=True)
    employee_account_id = fields.Many2one('account.account',string="Employee Account")  

    # policy_id = fields.Many2one('loan.policies',string='Policy',domain=lambda self:self._get_emp_domain())
    policy_id = fields.Many2one('loan.policies',string='Policy')
    notes = fields.Text(string="Notes")

    stage = fields.Selection([('draft','Draft'),('applied','Applied'),('waiting_depart','department approval'),('waiting','hr approval'),('approve','Approved'),('cancel','Cancel'),('disbursed','Disbursed')],default='draft' , tracking=3, index=True, copy=False)

    installment_ids = fields.One2many('loan.installment','loan_id')
    is_compute = fields.Boolean(string="Is Compute",copy=False)
    currency_id = fields.Many2one('res.currency',string="Currency",related="company_id.currency_id")

    journal_count = fields.Integer(string="loan count" , compute = "_check_loan_journal")
    move_entries = fields.Many2many('account.move','rel_move',string="Move Entries")

    loan_images_ids = fields.One2many('loan.image','loan_id','Document',required=True) 
    hide_proofs = fields.Boolean()
    first_installment = fields.Selection([('this', 'This Month'), ('next', 'Next Month')], default='this')
    first_installment_date = fields.Date(string="First Installment")

   # def write(self, vals):
    #    res = super(Loan_Request, self).write(vals)
      #  amount = sum(self.installment_ids.filtered(lambda x:not x.skip).mapped('principal_amount'))
      #  if self.principal_amount != round(amount,2) and self.installment_ids:
         #   raise ValidationError(_("Your Installment line amount not match to Total amount"))
       # return res

    def unlink(self):
        for rec in self:
            raise UserError(_("You cannot delete Loan Installment!"))
        return super(Loan_Request, self).unlink()

    @api.constrains('principal_amount')
    def _check_journal_entry(self):
        for record in self:
            if record.move_entries:
                if any([line.payment_state != 'not_paid' for line in record.move_entries]):
                    raise ValidationError(_('you can not change amount loan payment all ready done.'))

    @api.onchange('loan_type_id')
    def hide_proof_button(self):
        if self.loan_proof_ids:
            self.update({'hide_proofs':False})
        else:
            self.update({'hide_proofs': True})

    def copy(self, default=None):
        default = dict(default or {})
        default.update({'move_entries': False,'loan_entry_id': False,'interest_journal_id':False, 'account_entery_id' : False, 'policy_id': False,'applied_date': False,'approve_date': False,'disbursement_date': False,'stage': 'draft'})

        return super(Loan_Request, self).copy(default) 

    def loan_sequnce_genrate(self):
        loan_ids = self.env['loan.request'].search(['|',('name', '=', '/'), ('name', '=', '')])
        for loan in loan_ids:
            loan.name = self.env['ir.sequence'].next_by_code('loan.request') or '/'

    def action_resettodraft(self):
        self.write({'stage': 'draft'})

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.disburse_journal_id = self.employee_id.disburse_journal_id.id
            self.employee_account_id = self.employee_id.employee_account_id.id
            return {'domain': {'policy_id': ['|',('employee_ids','in',self.employee_id.ids),('employee_category_ids','in',self.employee_id.sudo().category_ids.ids)]}}

    @api.onchange('employee_id')
    def _onchange_employee_type_id(self):
        if self.employee_id:
            return {'domain': {'loan_type_id': ['|',('employee_ids','in',self.employee_id.ids),('employee_category_ids','in',self.employee_id.sudo().category_ids.ids)]}}

    def _check_loan_journal(self):
        for loan in self:
            if loan.move_entries:
                loan.journal_count = len(loan.move_entries)
            else:
                loan.journal_count = 0    

    def show_account_move(self):
        self.ensure_one()
        return {
            'name': 'Move Details',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', [x.id for x in self.move_entries])], 
        }

    @api.depends('loan_type_id', 'employee_id','policy_id','principal_amount')
    def _check_employee(self):
        if self.employee_id not in self.loan_type_id.employee_ids and self.employee_id.category_ids.ids not in self.loan_type_id.employee_category_ids.ids:
            raise ValidationError(_("Employee is not allowed to request for this loan type."))
        else: 
            return
        return



    @api.depends('installment_ids.state','total_loan')
    def _compute_balance_on_loan(self):
        for loan in self :
            total_paid = 0.0
            for line in loan.installment_ids :
                if line.state == 'paid':
                    total_paid = total_paid + line.emi_installment

            loan.received_from_employee = total_paid
            loan.balance_on_loan = loan.total_loan - total_paid
        return



    @api.depends('principal_amount','rate','duration_months')
    def _compute_loan_amounts(self):
        for line in self :
            line.total_interest = 0.0
            line.total_loan = 0.0
            if line.principal_amount > 0 and line.rate > 0 and line.is_interest_payable and line.loan_type_id.is_interest_payable:
                if line.loan_type_id.interest_mode == 'flat' :
                    line.total_interest = (line.principal_amount*line.rate)/100
                        
                    line.total_loan = line.total_interest + line.principal_amount
                elif line.loan_type_id.interest_mode == 'reducing' :
                    if line.duration_months > 0 :
                        principal_amount = line.principal_amount/line.duration_months
            
                        interest_amount = line.total_interest/line.duration_months

                        months = line.duration_months
                        amount_to_pay = line.principal_amount
                        total = 0.0 
                        for number in range(1,line.duration_months+1):

                            if months > 0 :
                                 
                                full_amount = amount_to_pay/months
                            
                                if amount_to_pay <= 0 :
                                    break
                                a = (full_amount*line.rate)/100
                                full_interest = a
                                    #months = months - 1 
                                amount_to_pay = amount_to_pay - principal_amount 
                                total = total + full_interest
                                line.total_interest = total     
                                line.total_loan = line.total_interest + line.principal_amount
            else:

                line.total_loan += line.principal_amount
        return

    def action_confirm(self):  
        total = 0
        count = 0  
        if self.loan_images_ids:            
            for test in self.loan_images_ids:
                for rec in test.loan_type_ids:
                    if rec in self.loan_proof_ids:
                        if rec.mandatory == True:
                            count+=1

            if self.loan_proof_ids:                
                for record in self.loan_proof_ids:
                    proof = self.env['loan.proof'].search([('id','=',record.id)])
                    if proof.mandatory == True:
                        total+=1
                    else:
                        pass                        
            if total == count:
                pass
            else:
                raise ValidationError(_("Please Upload Loan Mandatory Document.")) 
        else:
            if self.loan_proof_ids:
                for record in self.loan_proof_ids:
                    proof =self.env['loan.proof'].search([('id','=',record.id)])
                    if proof.mandatory == True:
                        raise ValidationError(_("Please Upload Loan Mandatory Document."))
                    else:
                        pass
                                       
        if self.policy_id :
            max_value = 0.0
            value_gap = 0
            is_max = False
            
            if self.policy_id.policy_type == 'max' and self.policy_id.basis == 'fix'  :
                is_max = True
                if self.policy_id.values > max_value :
                    max_value = self.policy_id.values

            if self.policy_id.policy_type == 'gap' :
                if self.policy_id.duration_months > value_gap :
                    value_gap = self.policy_id.duration_months
                    

            if value_gap > 0 :
                loan_res = self.env['loan.request'].search([('employee_id','=',self.employee_id.id),('stage','=','disbursed')])
                loan_dates = []
                for emp in loan_res :

                    if emp.id == self.id :
                        continue 
                    last_date = emp.applied_date + relativedelta(months=+emp.duration_months)
                    loan_dates.append(last_date)

                
                if len(loan_dates) > 0:
                    validate_date = max(loan_dates)
                
                    
                    date_1 = validate_date + relativedelta(months=+value_gap)

                    if self.applied_date < date_1 :
                        
                        r = relativedelta(date_1, self.applied_date)
                        
                        time = r.months
                        if r.years > 0:
                            time = time + (r.years * 12)
                        raise ValidationError(_("You can not apply for loan in next  %s   months") % time ) 


            if self.principal_amount > max_value and is_max == True:
                raise ValidationError(_("Your maximum amount to apply for loan is %s ") % max_value) 
                

        # template_id = self.env['ir.model.data'].get_object_reference(
        #                                       'bi_hr_employee_loan',
        #                                       'email_template_apply_loan_request')[1]
        # template_id = self.env.ref('bi_hr_employee_loan.email_template_apply_loan_request')
        # email_template_obj = self.env['mail.template'].sudo().browse(template_id)
        # user_ids = []
        # for user in self.env['res.users'].search([]):
        #     if self.env.ref('bi_hr_employee_loan.hr_loan_department_id') in user.groups_id:
        #         user_ids.append(user.partner_id.id)
        # users = set(user_ids)
        # user_ids = list(users)
        # if template_id:
        #     values = email_template_obj.generate_email(self.id, fields=['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
        #     values['email_from'] = self.employee_id.work_email or self.employee_id.user_id.email
        #     values['recipient_ids'] = user_ids
        #     values['res_id'] = False
        #     values['notification'] = True
        #     mail_mail_obj = self.env['mail.mail']
        #     msg_id = mail_mail_obj.sudo().create(values)
        #     if msg_id:
        #         mail_mail_obj.send([msg_id])


        self.write({'stage':'applied','applied_date' : fields.datetime.now()})
        return

    def action_department_approve(self):

        if self.policy_id :
            max_days = 0
            if self.policy_id.policy_type == 'qualifying' and self.policy_id.days > 0:
                if self.policy_id.days > max_days :
                    max_days = self.policy_id.days
            if max_days > 0 :
                end_date = self.applied_date + relativedelta(days=+max_days)
                if end_date > fields.datetime.today().date() :
                    raise ValidationError(_("You can approve this loan after  %s ") % end_date ) 

        # template_id = self.env['ir.model.data'].get_object_reference(
        #                                       'bi_hr_employee_loan',
        #                                       'email_template_dept_approved_loan_request')[1]
        # email_template_obj = self.env['mail.template'].sudo().browse(template_id)
        self.write({'department_employee_id':self.env.user.employee_id.id })
        user_ids = []
        # for user in self.env['res.users'].search([]):
        #     if self.env.ref('bi_hr_employee_loan.hr_loan_manager_id') in user.groups_id:
        #         user_ids.append(user.partner_id.id)
        # users = set(user_ids)
        # user_ids = list(users)
        # if template_id:
        #     values = email_template_obj.generate_email(self.id, fields=['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
        #     values['email_from'] = self.env.user.employee_id.work_email or self.env.user.partner_id.email
        #     values['recipient_ids'] = user_ids
        #     values['res_id'] = False
        #     values['notification'] = True
        #     mail_mail_obj = self.env['mail.mail']
        #     msg_id = mail_mail_obj.sudo().create(values)
        #     if msg_id:
        #         mail_mail_obj.send([msg_id])
        self.write({'stage':'waiting_depart','approve_date' : fields.datetime.now()})

        return                

    def action_approve(self):
        request_id = self
        if self.policy_id :
            max_days = 0
            
            if self.policy_id.policy_type == 'qualifying' and self.policy_id.days > 0:
                if self.policy_id.days > max_days :
                    max_days = self.policy_id.days

            if max_days > 0 :
                end_date = self.applied_date + relativedelta(days=+max_days)
                if end_date > fields.datetime.today().date() :
                    raise ValidationError(_("You can approve this loan after  %s ") % end_date ) 
        self.write({'hr_employee_id':self.env.user.employee_id.id })
        # template_id = self.env['ir.model.data'].get_object_reference(
        #                                       'bi_hr_employee_loan',
        #                                       'email_template_hr_approved_loan_request')[1]
        # email_template_obj = self.env['mail.template'].sudo().browse(template_id)
        user_ids = []
        for user in self.env['res.users'].search([]):
            if self.env.ref('bi_hr_employee_loan.hr_loan_accountant_id') in user.all_group_ids:
                user_ids.append(user.partner_id.id)
        users = set(user_ids)
        user_ids = list(users)
        # if template_id:
        #     values = email_template_obj.generate_email(self.id, fields=['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
        #     values['email_from'] = self.employee_id.work_email or self.employee_id.user_id.email
        #     values['recipient_ids'] = user_ids
        #     values['res_id'] = False
        #     values['notification'] = True
        #     mail_mail_obj = self.env['mail.mail']
        #     msg_id = mail_mail_obj.sudo().create(values)
        #     if msg_id:
        #         mail_mail_obj.send([msg_id])

        request_id.write({'stage':'waiting','approve_date' : fields.datetime.now()})
        
        return

    def action_cancel_dep(self):
        ctx = {}
        ctx.update({
            'loan_id' : self.id
            })
        return {
                'type': 'ir.actions.act_window',
                'name': 'Reject Loan Message',
                'res_model': 'reject.request',
                'view_mode': 'form',
                'context' : ctx,
                'target': 'new'
            }         
    def action_cancel_hr(self):
        ctx = {}
        ctx.update({
            'loan_id' : self.id
            })
        return {
                'type': 'ir.actions.act_window',
                'name': 'Reject Loan Message',
                'res_model': 'reject.request',
                'view_mode': 'form',
                'context' : ctx,
                'target': 'new'
            }
    def action_cancel_acc(self):
        ctx = {}
        ctx.update({
            'loan_id' : self.id
            })
        return {
                'type': 'ir.actions.act_window',
                'name': 'Reject Loan Message',
                'res_model': 'reject.request',
                'view_mode': 'form',
                'context' : ctx,
                'target': 'new'
            }            
                            
    @api.model
    def create(self, vals):
        if 'employee_id' in vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('loan.request') or '/'
            emp = self.env['hr.employee'].browse(vals.get('employee_id'))
            count = 0
            total = 0 
            if emp.id:
                if 'loan_type_id' in vals:
                    loan_type = self.env['loan.type'].browse(vals.get('loan_type_id'))
                    if loan_type.id:
                        if emp.id not in loan_type.employee_ids.ids and emp.sudo().category_ids not in loan_type.sudo().employee_category_ids:
                            raise ValidationError(_("Employee is not allowed to request for this loan type."))    
                if vals.get('loan_images_ids'):            

                    for test in vals.get('loan_images_ids'):
                        result =  test   
                        desired_id = result[2]["loan_type_ids"][0][2]
                        for rec in desired_id:
                            if vals.get('loan_proof_ids'):
                                for record in vals.get('loan_proof_ids'):
                                    if rec in record[2]:
                                        proof = self.env['loan.proof'].search([('id','=',rec)])
                                        if proof.mandatory == True:
                                            count+=1

                    if vals.get('loan_proof_ids'):                   
                        for record in vals.get('loan_proof_ids'):
                            for value in record[2]:
                                proof = self.env['loan.proof'].search([('id','=',value)])
                                if proof.mandatory == True:

                                    total+=1
                                else:
                                    pass        
                    if total == count:
                        pass
                    else:
                        raise ValidationError(_("Please Upload Loan Mandatory Document."))
                else:
                    if vals.get('loan_proof_ids'):
                        for record in vals.get('loan_proof_ids'):
                            for value in record[2]:
                                proof = self.env['loan.proof'].search([('id','=',value)])
                                if proof.mandatory == True:
                                    raise ValidationError(_("Please Upload Loan Mandatory Document."))
                                else:
                                    pass
        return super(Loan_Request, self).create(vals)

    def compute_loan(self):
        amount = sum(self.installment_ids.mapped('principal_amount'))
        first_installment_rec = self.installment_ids.filtered(lambda r: r.installment_number == 1)
        if self.duration_months != len(self.installment_ids) or self.principal_amount != amount or first_installment_rec.date_from != self.first_installment_date:
            month = self.first_installment_date.month
            year = self.first_installment_date.year
            principal_amount = self.principal_amount/self.duration_months
            if self.is_interest_payable:
                interest_amount = self.total_interest/self.duration_months
            else:
                interest_amount = 0.0
            installment_obj = self.env['loan.installment']
            installment_list = []

            months = self.duration_months
            amount_to_pay = self.principal_amount

            is_first = True
            for number in range(1,self.duration_months+1):
                if month == 12:
                    month = 1
                    year = year + 1
                else:
                    if is_first:
                        is_first = False
                        month = month
                    else:
                        month = month + 1
                start_date = datetime.date(year, month, 1)
                _, num_days = calendar.monthrange(year, month)
                end_date = datetime.date(year, month, num_days)

                # if self.first_installment == 'this':
                #     start_date = start_date - dateutil.relativedelta.relativedelta(months=1)
                #     end_date = end_date - dateutil.relativedelta.relativedelta(months=1)

                if self.interest_mode == "flat":
                    installment  = installment_obj.create({
                                        'loan_id' : self.id ,
                                        'employee_id':self.employee_id.id,
                                        'principal_amount':principal_amount,
                                        'interest_amount':interest_amount,
                                        'emi_installment' :principal_amount + interest_amount,
                                        'state' : 'unpaid',
                                        'currency_id' : self.company_id.currency_id.id,
                                        'loan_type_id' : self.loan_type_id.id ,
                                        'installment_number' : number,
                                        'date_from' : start_date,
                                        'date_to' : end_date,
                                        'payable_interest' : self.is_interest_payable,
                                        })
                elif self.interest_mode == "reducing":
                    if months > 0 :
                         
                        full_amount = amount_to_pay/months
                    
                    if amount_to_pay <= 0 :
                        break
                    a = (full_amount*self.rate)/100
                    if self.is_interest_payable:
                        full_interest = a
                    else:
                        full_interest = 0
                    
                    amount_to_pay = amount_to_pay - principal_amount
                    
                    installment  = installment_obj.create({
                                        'loan_id' : self.id ,
                                        'employee_id':self.employee_id.id,
                                        'principal_amount':principal_amount,
                                        'interest_amount':full_interest,
                                        'emi_installment' :principal_amount + full_interest,
                                        'state' : 'unpaid',
                                        'currency_id' : self.company_id.currency_id.id,
                                        'loan_type_id' : self.loan_type_id.id ,
                                        'installment_number' : number,
                                        'date_from' : start_date,
                                        'date_to' : end_date,
                                        'payable_interest' : self.is_interest_payable,
                                        })
                else:
                    installment  = installment_obj.create({'loan_id' : self.id ,'employee_id':self.employee_id.id,
                                        'principal_amount':principal_amount,
                                        'emi_installment' :principal_amount,'state' : 'unpaid',
                                        'currency_id' : self.company_id.currency_id.id,
                                        'loan_type_id' : self.loan_type_id.id ,
                                        'installment_number' : number,
                                        'date_from' : start_date,'date_to' : end_date,'payable_interest' : self.is_interest_payable,
                                        }) 


                installment_list.append(installment.id)


            self.installment_ids = [(6,0,installment_list)]
            res = self.env['account.move']

            name_of = self.employee_id.name
            loan_product_id = self.env['product.product'].search([('default_code', '=', 'Loan'), ('type', '=', 'service')])
            if not loan_product_id:
                loan_product_id = self.env['product.product'].create({'name': 'Loan',
                                                   'default_code': 'Loan',
                                                   'type': 'service',
                                                   'list_price': 0,
                                                   'taxes_id': False
                                                   })
             
            # debit_line = (0,0,{'account_id' : self.disburse_journal_id.default_account_id.id,
            #                     'employee_id' : self.employee_id.id,
            #                     'name' : 'Loan Of ' + name_of,
            #                     'debit' : self.principal_amount,
            #                     'credit' : 0.0
            #                     })


            # credit_line = (0,0,{'account_id' : self.employee_account_id.id,
            #                     'employee_id' : self.employee_id.id,
            #                     'name' : 'Loan Of ' + name_of,
            #                     'debit' : 0.0,
            #                     'credit' : self.principal_amount
            #                     })

            # move_line = [debit_line,credit_line]

            move_line = []

            # bill_journal_id = self.env['account.journal'].search([('type','=', 'purchase')], limit=1)
            partner_id = self.employee_id.partner_id
            if not partner_id:
                partner_id = self.env['res.partner'].create({'name': self.employee_id.name})
                self.employee_id.partner_id = partner_id.id

            # jounral = res.create({'date': fields.datetime.now(),
            #                       'move_type': 'in_invoice',
            #                       'journal_id' : self.disburse_journal_id.id,
            #                       'ref' : str(self.name) ,
            #                       'loan_ids': self,
            #                       'invoice_line_ids' : move_line,
            #                       'is_loan_slip' : True,
            #                       'partner_id': partner_id.id})

            if self.move_entries:
                move_entrie_id = self.move_entries[0]
                if move_entrie_id.payment_state == 'not_paid':
                    if move_entrie_id.state == 'draft':
                        if move_entrie_id.amount_total != self.principal_amount:
                            if move_entrie_id.invoice_line_ids:
                                line_id = move_entrie_id.invoice_line_ids[0]
                                line_id.with_context(check_move_validity=False).write({'price_unit': self.principal_amount})
                                line_id.move_id.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                    if move_entrie_id.amount_total != self.principal_amount:
                        if move_entrie_id.state == 'posted':
                            if move_entrie_id.invoice_line_ids:
                                line_id = move_entrie_id.invoice_line_ids[0]
                                move_entrie_id.button_draft()
                                line_id.with_context(check_move_validity=False).write({'price_unit': self.principal_amount})
                                line_id.move_id.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
                                move_entrie_id.action_prepost()
                                move_entrie_id.action_post()

            if not self.env.context.get('is_re_compute_button') and not self.move_entries:
                jounral = self.env['account.move'].create({
                    'move_type': 'in_invoice',
                    'partner_id': partner_id.id,
                    'date': fields.datetime.now(),
                    'is_expense': True,
                    'invoice_date': fields.datetime.now(),
                    'invoice_line_ids': [(0, 0, {
                        'name': loan_product_id.name,
                        'product_id': loan_product_id.id,
                        'quantity': 1,
                        'tax_ids': False,
                        'price_unit': self.principal_amount,
                    })],
                })

                self.write({'loan_entry_id':jounral.id,'move_entries': [(4, jounral.id)] })

            # template_id = self.env['ir.model.data'].get_object_reference(
            #                                       'bi_hr_employee_loan',
            #                                       'email_template_accountant_approved_loan_request')[1]
            # email_template_obj = self.env['mail.template'].sudo().browse(template_id)
            # if template_id:
            #     values = email_template_obj.generate_email(self.id, fields=['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
            #     values['email_from'] = self.env.user.email
            #     values['email_to'] = self.employee_id.work_email or self.employee_id.user_id.email
            #     values['res_id'] = False
            #     values['notification'] = True
            #     mail_mail_obj = self.env['mail.mail']
            #     msg_id = mail_mail_obj.sudo().create(values)
            #     if msg_id:
            #         mail_mail_obj.send([msg_id])
            self.account_employee_id = self.env.user.employee_id.id
            self.is_compute = True
            self.stage = "approve"
            loan_installment_ids = self.env['loan.installment'].search([('loan_id', '=', False)])
            loan_installment_ids.unlink()
        else:
            self.stage = "approve"
        return

    def disburse_loan(self):

        left_installment = len(self.installment_ids.search([('state','not in',['paid','postpone']),('loan_id','=',self.id)]))
        if left_installment: 
            raise ValidationError(_("%s , %d loan installment left , without paid all installment , loan not going to close.") % (self.name , left_installment))
        for line in self.installment_ids : 
            if self.loan_type_id.disburse_method == "direct" :
                line.pay_from_payroll = True

            elif self.loan_type_id.disburse_method == "payroll" :
                line.pay_from_payroll = False

        res = self.env['account.move']

        name_of = self.employee_id.name
        
        debit_line = (0,0,{'account_id' : self.employee_account_id.id,
                           'employee_id' : self.employee_id.id,
                            'name' : 'Loan Of ' + name_of,
                            'debit' : self.principal_amount,
                            'credit' : 0.0
                            })


        credit_line = (0,0,{'account_id' :  self.disburse_journal_id.default_account_id.id,
                            'employee_id' : self.employee_id.id,
                            'name' : 'Loan Of ' + name_of,
                            'debit' : 0.0,
                            'credit' : self.principal_amount
                            })

        move_line = [debit_line,credit_line]

        jounral = res.create({'date': fields.datetime.now(),
                    'journal_id' :self.disburse_journal_id.id,
                    'ref' : str(self.name) ,
                    'loan_ids': self,
                    'line_ids' : move_line})
        template_id = self.env['ir.model.data'].get_object_reference(
                                              'bi_hr_employee_loan',
                                              'email_template_disburse')[1]
        email_template_obj = self.env['mail.template'].sudo().browse(template_id)
        if template_id:
            values = email_template_obj.generate_email(self.id, fields=['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
            values['email_from'] = self.env.user.email
            values['email_to'] = self.employee_id.work_email or self.employee_id.user_id.email
            values['res_id'] = False
            values['notification'] = True
            mail_mail_obj = self.env['mail.mail']
            msg_id = mail_mail_obj.sudo().create(values)
            if msg_id:
                mail_mail_obj.send([msg_id])   
        self.write({'stage' : 'disbursed','account_entery_id':jounral.id ,'disbursement_date' : fields.datetime.now()})

class ir_attachment(models.Model):
    _inherit='ir.attachment'

    machine_repair_id  =  fields.Many2one('loan.request', 'loan request')  
