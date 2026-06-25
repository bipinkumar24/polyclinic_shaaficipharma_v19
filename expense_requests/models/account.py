from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class Emp(models.Model):
    _name = 'emp.fee'
    _description = 'Employee Fee'

    account_id = fields.Many2one('account.move', string='account')
    employees_id = fields.Many2one('res.partner', string='Name')
    description = fields.Text('Description')
    Amount = fields.Char(string=" Amount $")
    scheduled_date = fields.Date(string='Date')
    phone = fields.Char(string='Tell')


class Account(models.Model):
    _inherit = 'account.move'

    is_expense = fields.Boolean(string='Is Expense')
    department_id = fields.Many2one('hr.department', string='Department')
    employees_fee_ids = fields.One2many('emp.fee', 'account_id', string=' ')
    amount_paid = fields.Float(string="amount_paid")

    def _get_default_department(self):
        user = self.env.user
        return user.department_id.id if user.department_id else False

    def search(self, args, **kwargs):
        if self.env.context.get('default_is_expense', False):
            if self.env.user.has_group('expense_requests.can_request_expenses'):
                args += [('create_uid', '=', self.env.user.id)]
            if self.env.user.has_group('expense_requests.expensess_manager'):
                args += ['|', ('user_id.department_id', '=', self.env.user.department_id.id),
                         ('user_id.department_id', 'child_of', self.env.user.department_id.id)]
            if self.env.user.has_group('expense_requests.all_expensess_manager'):
                args += [(1, '=', 1)]
        return super(Account, self).search(args, **kwargs)

    @api.model
    def create(self, vals):
        rec = super(Account, self).create(vals)
        # self.clear_caches()
        required_fields = ''
        for field in rec.next_approval_id.fields_ids:
            required_fields += field.field_description + ", "
        for field in rec.next_approval_id.fields_ids:
            if self.env['account.move'].search([(field.name, '=', False), ('id', '=', rec.id)]):
                raise ValidationError("Required Fields are %r" % required_fields)
        rec.remark_ids = [(0, 0, {'name': "New Created",
                                  'user_id': self.env.user.id,
                                  'remark_datettime': fields.Datetime.now(),
                                  'to_stage_id': rec.next_approval_id.id,
                                  'remark_type': 'approve'
                                  })]
        return rec

    def write(self, vals):
        for rec in self:
            required_fields = ' '
            for field in rec.next_approval_id.fields_ids:
                required_fields += field.field_description + ","
            for field in rec.next_approval_id.fields_ids:
                if not vals.get(field.name):
                    if self.env['account.move'].search([(field.name, '=', False), ('id', '=', rec.id)]):
                        raise ValidationError("Required Fields are %r" % required_fields)
            # self.clear_caches()
            res = super(Account, self).write(vals)
            return res

    def _compute_is_customer_doc_required(self):
        for rec in self:
            rec.is_customer_doc_required = rec.next_approval_id.is_customer_doc_required

    def _write_company_type(self):
        for partner in self:
            partner.is_company = partner.company_type == 'company'

    @api.depends('next_approval_id', 'next_approval_id.approval_user_ids')
    def _compute_next_approval_user_id(self):
        for rec in self:
            rec.next_approval_user_ids = [(6, 0, rec.next_approval_id.approval_user_ids.ids)]

    @api.depends('next_approval_id', 'next_approval_user_ids')
    def _compute_is_button(self):
        for rec in self:
            if rec.env.user.id in rec.next_approval_user_ids.ids:
                rec.is_button = True
            else:
                rec.is_button = False

            if rec.next_approval_id.is_last_approval or rec.next_approval_id.is_reject:
                rec.is_button = False
            if rec.next_approval_id.is_last_approval:
                rec.is_last_level = True
            elif rec.state_2 == 'finance':
                rec.is_last_level = True
            else:
                rec.is_last_level = False

    @api.depends('next_approval_id')
    def _compute_is_first(self):
        for rec in self:
            if rec.next_approval_id.level == 1:
                rec.is_first = True
            else:
                rec.is_first = False

    not_finance = fields.Boolean(string='not finance', compute='_compute_not_finance')

    @api.depends('is_first', 'state_2', )
    def _compute_not_finance(self):
        for rec in self:
            if rec.is_first == True and rec.require_hr == False:
                rec.not_finance = True
            elif rec.is_first == True and rec.require_hr == True and rec.state_2 != 'finance':
                rec.not_finance = True
            else:
                rec.not_finance = False

    def _get_next_approval_id(self):
        rec = self.env['approval.level.account'].search([('level', '=', 1)])
        return rec.id

    next_approval_id = fields.Many2one('approval.level.account', string='Next Approval', tracking=True,
                                       default=_get_next_approval_id)
    level = fields.Integer(related="next_approval_id.level")
    next_approval_user_ids = fields.Many2many('res.users', string='Next Approval By',
                                              compute='_compute_next_approval_user_id', store=True)
    is_button = fields.Boolean('Is button', compute='_compute_is_button')
    is_first = fields.Boolean('Is button ', compute='_compute_is_first')
    is_last_level = fields.Boolean(' Is button', compute='_compute_is_button')
    remark_ids = fields.One2many('remarks.approval.account', 'move_id', string='Remarks', tracking=True)
    is_customer_doc_required = fields.Boolean(string='Is Customer Doc Required',
                                              compute='_compute_is_customer_doc_required')
    require_hr = fields.Boolean(string='Requires HR Approval')
    require_gm = fields.Boolean(string='Requires GM Approval')
    require_custom_gm = fields.Boolean(string='Requires GM Approval ')
    department_approved = fields.Boolean(string='Require HR')
    next_is_reject = fields.Boolean(related='next_approval_id.is_reject', string='Next Is Reject', readonly=True )

    state_2 = fields.Selection(
        [
            ("new", "Draft"),
            ("depapproved", "Dep/site Manager Approved"),
            ("hr", "HR Approved"),
            ("togm", "Submitted to GM"),
            ("finance", "Submited for Payment"),
            ("reject", "Rejected"),

        ],
        string="Vehicle Status",
        default="new",
    )
    hide_hide_gm = fields.Boolean(string="Hide Gm", compute="_compute_hide_hide_gm")

    @api.onchange('invoice_line_ids', 'amount_total')
    def _onchange_tax_totals_json(self):
        for record in self:
            total_price_unit = 0
            if record.invoice_line_ids:
                total_price_unit = sum(line.price_unit for line in record.invoice_line_ids)
            return {
                'domain': {
                    'next_approval_id': [('maximum_amount', '<=', total_price_unit)]
                }
            }

    def gm_approve(self):
        for rec in self:
            rec.state_2 = 'finance'

    def _compute_hide_hide_gm(self):
        for account in self:
            if account.next_approval_id.level == 2:
                account.hide_hide_gm = False
            else:
                account.hide_hide_gm = True

    def cancel_it(self):
        for rec in self:
            rec.state_2 = 'reject'

    def submit_to_gm(self):
        for rec in self:
            rec.state_2 = 'togm'

    def department_approve(self):
        for rec in self:
            rec.department_approved = True
            rec.state_2 = 'depapproved'

            partner_ids = []
            group = self.env.ref('expense_requests.department_approver')
            for user in group.user_ids:
                if user.partner_id:
                    partner_ids.append(user.partner_id.id)

            fetchmail_server_id = self.env['fetchmail.server'].sudo().search([])
            user = ''
            if fetchmail_server_id:
                user = fetchmail_server_id[0].user

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)

            values = {'subject': 'Dept/Site Manager Approval',
                      'body_html': 'Dept/Site Manager Approval \n' + base_url,
                      'parent_id': None,
                      'email_from': self.env.user.email or None,
                      'auto_delete': False,
                      'recipient_ids': [(6, 0, partner_ids)],
                      }
            result = self.env['mail.mail'].sudo().create(values).send()

        return

    def hr_approve(self):
        for rec in self:
            rec.state_2 = 'hr'

            partner_ids = []
            for user in self.env.ref('expense_requests.hr_approver').user_ids:
                partner_ids.append(user.partner_id.id)

            fetchmail_server_id = self.env['fetchmail.server'].sudo().search([])
            user = ''
            if fetchmail_server_id:
                user = fetchmail_server_id[0].user

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)

            values = {'subject': 'HR Approval',
                      'body_html': 'HR Approval \n' + base_url,
                      'parent_id': None,
                      'email_from': self.env.user.email or None,
                      'auto_delete': False,
                      'recipient_ids': [(6, 0, partner_ids)],
                      }
            result = self.env['mail.mail'].sudo().create(values).send()

        return

    def finance_approve(self):
        for rec in self:
            rec.state_2 = 'finance'

            partner_ids = []
            for user in self.env.ref('expense_requests.Finance_approver').user_ids:
                partner_ids.append(user.partner_id.id)

            fetchmail_server_id = self.env['fetchmail.server'].sudo().search([])
            user = ''
            if fetchmail_server_id:
                user = fetchmail_server_id[0].user

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)

            values = {'subject': 'Finance Approval',
                      'body_html': 'Finance Approval \n' + base_url,
                      'parent_id': None,
                      'email_from': self.env.user.email or None,
                      'auto_delete': False,
                      'recipient_ids': [(6, 0, partner_ids)],
                      }
            result = self.env['mail.mail'].sudo().create(values).send()

        return

    def action_approve(self):
        view_id = self.env.ref('expense_requests.account_remark_wizard_view').id
        return {'type': 'ir.actions.act_window',
                'name': _('Remarks'),
                'res_model': 'account.remark.wizard',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }

    @api.depends('is_company')
    def _compute_company_type(self):
        for partner in self:
            partner.company_type = 'company' if partner.is_company else 'person'

    def submit_to_gm_dynamic(self):
        level_rec = self.env['approval.level.account'].search([('level', '=', 3)], limit=1)
        if level_rec:
            self.require_custom_gm = False
            self.next_approval_id = level_rec.id


    def gm_approve_custom(self):
        level_rec = self.env['approval.level.account'].search([('level', '=', 4)], limit=1)
        if level_rec:
            self.next_approval_id = level_rec.id

    def gm_approve_reject(self):
        level_rec = self.env['approval.level.account'].search([('is_reject', '=', True)], limit=1)
        if not level_rec:
            raise UserError(_("Please Configure Reject Level First or Contact to Administrator"))
        self.next_approval_id = level_rec.id
