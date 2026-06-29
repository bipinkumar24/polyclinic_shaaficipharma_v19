# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ChartfAccount(models.Model):
    _name = 'advance.salary'
    _rec_name = 'employee_id'


    name = fields.Char(string="Name")
    employee_id = fields.Many2one('hr.employee',string="Employee")
    req_date = fields.Datetime(string="Request Date", default=fields.Datetime.now, readonly=True)
    req_amount = fields.Monetary(string="Request Amount")
    currency_id = fields.Many2one('res.currency',string="Currency",default = lambda self : self.env.user.company_id.currency_id.id,readonly=True)

    department_id = fields.Many2one('hr.department',string="Department")
    job_id = fields.Many2one('hr.job',string="Job Position")
    department_manager_id = fields.Many2one('hr.employee',string="Manager")
    req_user_id = fields.Many2one('res.users',string="Request User")


    confirm_date = fields.Datetime(string="Confirm Date")
    approve_date_department = fields.Datetime(string="Approve Date(Department)")
    approve_date_hr = fields.Datetime(string="Approve Date(HR)")
    approve_date_director = fields.Datetime(string="Approve Date(Director)")
    paid_date = fields.Datetime(string="Paid Date")

    confirm_by_id = fields.Many2one('res.users',string="Confirm By")
    depet_manager_approve_by_id = fields.Many2one('res.users',string="Department Approve By")
    hr_manager_id = fields.Many2one('res.users',string="HR Manager")
    director_id = fields.Many2one('res.users',string="Director")
    paid_by_id = fields.Many2one('res.users',string="Paid By")
    company_id = fields.Many2one('res.company',string="Company", default=lambda self: self.env.company)

    partner_id = fields.Many2one('res.partner',string = "Employee Partner")
    payment_method_id = fields.Many2one('account.journal',string="Payment Method",domain=[('type','in',['bank','cash'])])
    payment_id = fields.Many2one('account.payment',string="Payment",readonly=True)


    state = fields.Selection([('draft','Draft'),('confirmed','Confirmed'),('approve_dept','Department Approve'),
                            ('approve_hr','HR Approve'),('approve_director','Director Approve'),
                              ('approved', 'Approved'),('partially_paid', 'Partially Paid'), ('paid','Paid'),('done','Done'), ('cancel', 'Cancel')]
                            ,default='draft')
    bill_id = fields.Many2one('account.move', string="Account Move")
    paid_amount = fields.Monetary(string="Paid Amount", compute="_compute_paid_amount")
    is_amount_status = fields.Boolean(string="is show", compute="_compute_is_amount_status_data", store=True)
    is_bulk_advance_salary = fields.Boolean(string="Is Bulk Advance Salary")
    bulk_advance_ids = fields.One2many('bulk.advance.salary', 'advance_id', string="Advance Salary")
    bill_ids = fields.Many2many('account.move', string="Account Moves")
    bill_count = fields.Integer(string="Bill", compute="_compute_bill_count")


    @api.depends('bill_ids.amount_total_signed', 'bill_ids.amount_residual', 'bill_ids.amount_total', 'bill_ids')
    def _compute_paid_amount(self):
        for rec in self:
            if rec.is_bulk_advance_salary:
                if rec.bill_ids and rec.state in ['partially_paid', 'paid', 'done']:
                    amount_paid = sum(rec.bill_ids.mapped('amount_total')) - sum(rec.bill_ids.mapped('amount_residual'))
                    rec.paid_amount = amount_paid
                else:
                    rec.paid_amount = 0
            else:
                if rec.bill_id and rec.state in ['partially_paid', 'paid', 'done']:
                    amount_paid = rec.bill_id.amount_total - rec.bill_id.amount_residual
                    rec.paid_amount = amount_paid
                else:
                    rec.paid_amount = 0

    def add_amount_paid(self):
        salary_ids = self.env['advance.salary'].search([('state', 'in', ['approved', 'partially_paid', 'paid', 'done'])])
        for rec in salary_ids:
            if rec.is_bulk_advance_salary:
                if rec.bill_ids:
                    amount_paid = sum(rec.bill_ids.mapped('amount_total')) - sum(rec.bill_ids.mapped('amount_residual'))
                    rec.paid_amount = amount_paid
            else:
                if rec.bill_id:
                    amount_paid = rec.bill_id.amount_total - rec.bill_id.amount_residual
                    rec.paid_amount = amount_paid

    @api.constrains('is_bulk_advance_salary')
    def _constrains_is_bulk_advance_salary(self):
        for order in self:
            if order.is_bulk_advance_salary and not order.bulk_advance_ids:
                raise ValidationError(_("Please Select at least one employee."))

    @api.constrains('bulk_advance_ids')
    def _check_salary_amount(self):
        for advance in self:
            for record in advance.bulk_advance_ids:
                if record.job_id and record.amount > record.job_id.salary_limit:
                    raise ValidationError(_("Employee %s request amount is more than your salary limit") % record.employee_id.name)
                if record.amount <= 0:
                    raise ValidationError(_("Please add Employee %s request amount") % record.employee_id.name)

    @api.depends('bill_id', 'bill_ids', 'bill_id.amount_total', 'bill_ids.amount_total', 'bill_id.amount_residual', 'bill_ids.amount_residual')
    def _compute_is_amount_status_data(self):
        for rec in self:
            if rec.is_bulk_advance_salary:
                if rec.state == 'approved':
                    if rec.bill_ids:
                        amount_paid = sum(rec.bill_ids.mapped('amount_total')) - sum(rec.bill_ids.mapped('amount_residual'))
                        if amount_paid != 0:
                            if amount_paid > 0:
                                rec.state = 'partially_paid'
                            else:
                                rec.state = 'paid'
                if rec.state == 'partially_paid':
                    if sum(rec.bill_ids.mapped('amount_residual')) == 0:
                        rec.state = 'paid'
                if rec.bill_ids:
                    amount_paid = sum(rec.bill_ids.mapped('amount_total')) - sum(rec.bill_ids.mapped('amount_residual'))
                    rec.paid_amount = amount_paid
                    rec.is_amount_status = True
                else:
                    rec.is_amount_status = False
                    rec.paid_amount = 0.00
            else:
                if rec.state == 'approved':
                    if rec.bill_id:
                        amount_paid = rec.bill_id.amount_total - rec.bill_id.amount_residual
                        if amount_paid != 0:
                            if amount_paid > 0:
                                rec.state = 'partially_paid'
                            else:
                                rec.state = 'paid'
                if rec.state == 'partially_paid':
                    if rec.bill_id.amount_residual == 0:
                        rec.state = 'paid'
                if rec.bill_id:
                    amount_paid = rec.bill_id.amount_total - rec.bill_id.amount_residual
                    rec.paid_amount = amount_paid
                    rec.is_amount_status = True
                else:
                    rec.is_amount_status = False
                    rec.paid_amount = 0.00

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def _compute_bill_count(self):
        for salary in self:
            total_len = len(salary.bill_id) + len(salary.bill_ids)
            salary.bill_count = total_len

    def action_view_bills(self):
        bill_data = []
        if self.bill_id:
            bill_data.append(self.bill_id.id)
        if self.bill_ids:
            bill_data.extend(self.bill_ids.ids)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', bill_data)],
            'target': 'current'
        }

    @api.onchange('employee_id')
    def onchange_employee(self):
        self.department_id = self.employee_id.department_id.id
        self.job_id = self.employee_id.job_id
        self.department_manager_id = self.employee_id.department_id.manager_id.id
        if self.employee_id:
            if self.employee_id.user_id:
                self.partner_id = self.employee_id.user_id.partner_id.id
            else:
                self.partner_id = self.employee_id.partner_id.id
        return

    def unlink(self):
        for order in self:
            if order.state not in ('draft',):
                raise ValidationError(_('You can not delete a  confirmed Request .'))
        return super(ChartfAccount, self).unlink()

    def _get_advance_salary_product(self):
        product = self.env['product.product'].search([
            ('default_code', '=', 'Advance_salary'),
            ('detailed_type', '=', 'service'),
        ], limit=1)
        if not product:
            product = self.env['product.product'].create({
                'name': 'Advance Salary',
                'default_code': 'Advance_salary',
                'detailed_type': 'service',
                'list_price': 0,
                'taxes_id': False,
            })
        return product

    def _get_advance_salary_expense_account(self, product):
        accounts = product.product_tmpl_id._get_product_accounts()
        expense_account = product.property_account_expense_id or accounts.get('expense')
        if not expense_account:
            raise ValidationError(
                _("No expense account is configured for product '%s'. Please configure the product or category expense account.")
                % product.display_name
            )
        return expense_account

    def action_pay(self):
        product_id = self._get_advance_salary_product()
        expense_account = self._get_advance_salary_expense_account(product_id)
        if self.is_bulk_advance_salary:
            for line in self.bulk_advance_ids:
                partner_id = line.partner_id 
                if not partner_id:
                    partner_id = self.env['res.partner'].create({'name': line.employee_id.name})
                    line.employee_id.partner_id = partner_id.id
                bill_id = self.env['account.move'].create({
                    'move_type': 'in_invoice',
                    'partner_id': partner_id.id,
                    'date': fields.Datetime.now(),
                    'invoice_date': fields.Datetime.now(),
                    'invoice_line_ids': [
                        (0, 0, {
                            'product_id' : product_id.id,
                            'account_id': expense_account.id,
                            'name': product_id.name,
                            'quantity': 1,
                            'price_unit': line.amount
                        })
                    ],
                })
                if not line.employee_id.bank_account_id:
                    raise ValidationError(
                        _("The employee '%s' does not have a bank account configured. "
                          "Please configure the bank account before proceeding.")
                        % (line.employee_id.name)
                    )

                message = f"""
                    <div style="background:#d9edf7;
                                padding:12px;
                                border-radius:6px;
                                border-left:5px solid #31708f;
                                font-family:Arial;
                                font-size:14px;">

                        <p style="margin:0;"><strong>Dear Cashier,</strong></p>

                        <p style="margin:4px 0 0 0;">
                            Kindly be informed that the bank account number for employee 
                            <strong>{line.employee_id.name}</strong> is 
                            <strong>{line.employee_id.bank_account_id.acc_number}</strong>.
                        </p>

                    </div>
                    """
                bill_id.message_post(
                    body=message,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )
                self.write({'bill_ids': [(4, bill_id.id, 0)]})
            self.write({'state':'approved'})
        else: 
            partner_id = self.partner_id
            if not partner_id:
                partner_id = self.env['res.partner'].create({'name': self.employee_id.name})
                self.employee_id.partner_id = partner_id.id

            if not self.employee_id.bank_account_id:
                raise ValidationError(
                    _("The employee '%s' does not have a bank account configured. "
                      "Please configure the bank account before proceeding.")
                    % (self.employee_id.name)
                )
            bill_id = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': partner_id.id,
                'date': fields.Datetime.now(),
                'invoice_date': fields.Datetime.now(),
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id' : product_id.id,
                        'account_id': expense_account.id,
                        'name': product_id.name,
                        'quantity': 1,
                        'price_unit': self.req_amount
                    })
                ],
            })
            message = f"""
                <div style="background:#d9edf7;
                            padding:12px;
                            border-radius:6px;
                            border-left:5px solid #31708f;
                            font-family:Arial;
                            font-size:14px;">

                    <p style="margin:0;"><strong>Dear Cashier,</strong></p>

                    <p style="margin:4px 0 0 0;">
                        Kindly be informed that the bank account number for employee 
                        <strong>{self.employee_id.name}</strong> is 
                        <strong>{self.employee_id.bank_account_id.acc_number}</strong>.
                    </p>

                </div>
            """
            bill_id.message_post(
                    body=message,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )
            if not self.partner_id:
                self.partner_id = partner_id.id
            self.write({'state':'approved',
                        'bill_id': bill_id.id})

    def action_confirm(self):
        if not self.is_bulk_advance_salary:
            if self.req_amount <= 0:
                raise UserError(_('Please add a valid request amount.'))
            if self.req_amount > self.employee_id.job_id.salary_limit : 
                raise UserError(_('Your request amount is more than your salary limit.'))
        self.write({'state':'confirmed','confirm_by_id':self.env.user.id,'confirm_date' : fields.Datetime.now()})

    def action_approve_dept(self):
        self.write({'state':'approve_dept','depet_manager_approve_by_id':self.env.user.id,'approve_date_department' : fields.Datetime.now()})

    def action_approve_hr(self):
        self.write({'state':'approve_hr','hr_manager_id':self.env.user.id,'approve_date_hr' : fields.Datetime.now()})


    def action_approve_director(self):
        self.write({'state':'approve_director','director_id':self.env.user.id,'approve_date_director' : fields.Datetime.now()})

    def action_done(self):
        employee_id = self.env['hr.employee'].search([('id','=',self.employee_id.id)])
        for employee in employee_id:
            if employee_id.payslip_count != 0:
                self.write({'state':'done'})
            else:
                raise UserError(_('Payslip is not created for this month.'))
        return

class Hr_job(models.Model) :
    _inherit = 'hr.job'

    salary_limit = fields.Float(string="Salary Limit",default = 0.0)


class Hr_employee_inherit_(models.Model):
    _inherit = "hr.employee"

    def get_advancesalary(self, id, start_date, end_date):
        advance_salary_ids = self.env['advance.salary'].search([('employee_id', '=', id), ('confirm_date', '>=', start_date),
                                                           ('confirm_date', '<=', end_date), ('state', '=', 'paid')])

        bulk_ids = self.env['bulk.advance.salary'].search([('employee_id', '=', id),
                                                           ('advance_id.confirm_date', '>=', start_date),
                                                           ('advance_id.confirm_date', '<=', end_date),
                                                           ('advance_id.state', '=', 'paid')])
        total = 0.0
        for line in advance_salary_ids:
            if line.paid_amount > 0:
                total = total + line.paid_amount
            else:
                total = total + (line.paid_amount * -1)
        for line in bulk_ids:
            if not line.advance_id.id in advance_salary_ids.ids:
                if line.amount > 0:
                    total = total + line.amount
                else:
                    total = total + (line.amount * -1)
        if total > 0:
            return total * -1
        else:
            return total

class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def action_create_payments(self):
        res = super(AccountPaymentRegister, self).action_create_payments()
        for rec in self:
            if rec.payment_difference < 0:
                raise ValidationError(_("You Can Not Pay More Than Payment Amount!"))
        return res

class BulkAdvanceSalary(models.Model):
    _name = 'bulk.advance.salary'
    _description = "Bulk Advance Salary"

    advance_id = fields.Many2one('advance.salary', string="Advance Salary ")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    amount = fields.Float(string="Amount")
    partner_id = fields.Many2one('res.partner', string="Partner")
    job_id = fields.Many2one('hr.job',string="Job Position")

    @api.onchange('employee_id')
    def set_partner_based_employee(self):
        if self.employee_id:
            if not self.employee_id.partner_id:
                raise ValidationError(_("Please set an employee in the partner before proceeding."))
            else:
                self.partner_id = self.employee_id.partner_id.id
            if self.employee_id.job_id:
                self.job_id = self.employee_id.job_id.id

class AccountMove(models.Model):
    _inherit = "account.move"

    mobile_phone = fields.Char(string="Mobile Number", compute='_compute_mobile_number')

    def _compute_mobile_number(self):
        for rec in self:
            if rec.partner_id:
                employee_id = self.env['hr.employee'].search([('partner_id', '=', rec.partner_id.id)], limit=1)
                rec.mobile_phone = employee_id.mobile_phone
            else:
                rec.mobile_phone = " "
