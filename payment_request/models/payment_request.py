from odoo import api, fields, models, _
from odoo.exceptions import UserError


REQUEST_TYPE_SELECTION = [
    ('loan', 'Loan'),
    ('advance', 'Salary Advance'),
    ('overtime', 'Overtime'),
    ('purchase', 'Purchase Request'),
    ('expense', 'Expense'),
    ('other', 'Other'),
]

PRIORITY_SELECTION = [
    ('0', 'Normal'),
    ('1', 'High'),
    ('2', 'Urgent'),
]

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('reviewed', 'Reviewed by Manager'),
    ('verified', 'Verified by Finance'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('cancelled', 'Cancelled'),
]

LOAN_PURPOSE_SELECTION = [
    ('emergency_medical', 'Emergency Medical'),
    ('education', 'Education / Training'),
    ('housing', 'Housing / Rent'),
    ('vehicle', 'Vehicle Purchase'),
    ('wedding', 'Wedding / Family Event'),
    ('debt_settlement', 'Debt Settlement'),
    ('personal', 'Personal'),
    ('other', 'Other'),
]

REPAYMENT_METHOD_SELECTION = [
    ('salary_deduction', 'Monthly Salary Deduction'),
    ('lump_sum', 'Lump Sum Repayment'),
    ('custom', 'Custom Schedule'),
]


class PaymentRequest(models.Model):
    _name = 'payment.request'
    _description = 'Payment Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc, id desc'
    _rec_name = 'name'

    # ── Core ─────────────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default=lambda self: _('New'),
        tracking=True,
    )
    request_type = fields.Selection(
        REQUEST_TYPE_SELECTION,
        string='Request Type',
        required=True,
        tracking=True,
        default='expense',
    )
    state = fields.Selection(
        STATE_SELECTION,
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    request_priority = fields.Selection(
        PRIORITY_SELECTION,
        string='Priority',
        default='0',
        tracking=True,
    )
    description = fields.Text(string='Justification / Description', required=True)
    amount_requested = fields.Monetary(
        string='Amount Requested',
        required=True,
        currency_field='currency_id',
        tracking=True,
    )
    amount_approved = fields.Monetary(
        string='Amount Approved',
        currency_field='currency_id',
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        check_company=True,
        tracking=True,
        help='Analytic account propagated to the generated bill lines.',
    )
    account_id = fields.Many2one(
        'account.account',
        string='Account',
        check_company=True,
        tracking=True,
        help='Account set on the generated bill lines.',
    )

    # ── People ────────────────────────────────────────────────────────────────────
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner (Billing)',
        tracking=True,
        help='Partner used for bill generation. Auto-created from employee if not set.',
    )
    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    reviewed_by = fields.Many2one('res.users', string='Reviewed By (Manager)',
                                   readonly=True, tracking=True, copy=False)
    verified_by = fields.Many2one('res.users', string='Verified By (Finance)',
                                   readonly=True, tracking=True, copy=False)
    approved_by = fields.Many2one('res.users', string='Final Approved By',
                                   readonly=True, tracking=True, copy=False)
    rejected_by = fields.Many2one('res.users', string='Rejected By',
                                   readonly=True, copy=False)

    # ── Dates ─────────────────────────────────────────────────────────────────────
    date_request = fields.Date(
        string='Request Date', required=True,
        default=fields.Date.today, tracking=True,
    )
    date_reviewed = fields.Datetime(string='Reviewed On', readonly=True, copy=False)
    date_verified = fields.Datetime(string='Verified On', readonly=True, copy=False)
    date_approved = fields.Datetime(string='Approved On', readonly=True, copy=False)
    date_rejected = fields.Datetime(string='Rejected On', readonly=True, copy=False)
    date_needed = fields.Date(string='Date Needed By')

    # ── Approval notes ────────────────────────────────────────────────────────────
    manager_note = fields.Text(string='Manager Note', copy=False)
    finance_note = fields.Text(string='Finance Note', copy=False)
    approver_note = fields.Text(string='Approver Note', copy=False)
    rejection_reason = fields.Text(string='Rejection Reason', copy=False, tracking=True)

    # ── Loan fields ───────────────────────────────────────────────────────────────
    loan_purpose = fields.Selection(LOAN_PURPOSE_SELECTION, string='Loan Purpose')
    loan_repayment_months = fields.Integer(string='Repayment Period (months)')
    loan_repayment_method = fields.Selection(
        REPAYMENT_METHOD_SELECTION,
        string='Repayment Method',
        default='salary_deduction',
    )
    loan_monthly_deduction = fields.Monetary(
        string='Monthly Deduction',
        currency_field='currency_id',
        compute='_compute_loan_monthly',
        store=True,
    )
    loan_first_deduction_date = fields.Date(string='First Deduction Date')
    loan_guarantor = fields.Char(string='Guarantor Name')
    loan_guarantor_id_no = fields.Char(string='Guarantor ID Number')
    loan_guarantor_phone = fields.Char(string='Guarantor Phone')
    loan_collateral = fields.Text(string='Collateral / Security')
    loan_existing_loans = fields.Monetary(
        string='Existing Outstanding Loans',
        currency_field='currency_id',
        help='Total outstanding balance of previous loans for this employee.',
    )
    loan_total_debt = fields.Monetary(
        string='Total Debt After Approval',
        currency_field='currency_id',
        compute='_compute_loan_total_debt',
        store=True,
    )
    loan_terms_accepted = fields.Boolean(string='Employee Accepts Loan Terms')
    loan_disbursement_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ], string='Disbursement Method', default='bank_transfer')
    loan_bank_account = fields.Char(string='Employee Bank Account / IBAN')
    loan_interest_rate = fields.Float(
        string='Interest Rate (%)', digits=(5, 2),
        help='Annual interest rate. Leave 0 for interest-free loans.',
    )
    loan_total_repayable = fields.Monetary(
        string='Total Repayable Amount',
        currency_field='currency_id',
        compute='_compute_loan_total_repayable',
        store=True,
    )
    loan_purpose_detail = fields.Text(string='Purpose Detail / Explanation')

    # ── Bill tracking ─────────────────────────────────────────────────────────────
    bill_id = fields.Many2one(
        'account.move',
        string='Generated Bill',
        readonly=True,
        copy=False,
        tracking=True,
    )
    bill_count = fields.Integer(compute='_compute_bill_count', string='Bills')

    # ── Salary Advance ────────────────────────────────────────────────────────────
    advance_month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Advance Month')
    advance_year = fields.Integer(
        string='Advance Year',
        default=lambda self: fields.Date.today().year,
    )
    advance_percentage = fields.Float(string='% of Salary', digits=(5, 2))

    # ── Overtime ──────────────────────────────────────────────────────────────────
    overtime_hours = fields.Float(string='Overtime Hours')
    overtime_date = fields.Date(string='Overtime Work Date')
    overtime_rate = fields.Float(string='Hourly Rate', digits=(10, 2))

    # ── Purchase ──────────────────────────────────────────────────────────────────
    vendor_name = fields.Char(string='Vendor Name')
    po_reference = fields.Char(string='PO Reference')
    purchase_line_ids = fields.One2many(
        'payment.request.line', 'request_id', string='Purchase Items',
    )
    purchase_total = fields.Monetary(
        string='Purchase Total',
        currency_field='currency_id',
        compute='_compute_purchase_total',
        store=True,
    )

    # ── Expense ───────────────────────────────────────────────────────────────────
    expense_category = fields.Selection([
        ('travel', 'Travel'),
        ('accommodation', 'Accommodation'),
        ('meals', 'Meals & Entertainment'),
        ('communication', 'Communication'),
        ('stationery', 'Stationery & Office'),
        ('training', 'Training & Education'),
        ('other', 'Other'),
    ], string='Expense Category')
    expense_period_from = fields.Date(string='Period From')
    expense_period_to = fields.Date(string='Period To')

    # ── Attachments ───────────────────────────────────────────────────────────────
    attachment_ids = fields.Many2many('ir.attachment', string='Supporting Documents')

    # ── Access buttons (computed, non-stored) ─────────────────────────────────────
    can_submit = fields.Boolean(compute='_compute_access_buttons')
    can_review = fields.Boolean(compute='_compute_access_buttons')
    can_verify = fields.Boolean(compute='_compute_access_buttons')
    can_approve = fields.Boolean(compute='_compute_access_buttons')
    can_reject = fields.Boolean(compute='_compute_access_buttons')
    can_cancel = fields.Boolean(compute='_compute_access_buttons')

    # ── Computes ──────────────────────────────────────────────────────────────────

    @api.depends('amount_requested', 'loan_repayment_months')
    def _compute_loan_monthly(self):
        for rec in self:
            if rec.loan_repayment_months and rec.loan_repayment_months > 0:
                rec.loan_monthly_deduction = rec.amount_requested / rec.loan_repayment_months
            else:
                rec.loan_monthly_deduction = 0.0

    @api.depends('amount_requested', 'loan_interest_rate', 'loan_repayment_months')
    def _compute_loan_total_repayable(self):
        for rec in self:
            if rec.loan_interest_rate and rec.loan_repayment_months:
                monthly_rate = rec.loan_interest_rate / 100 / 12
                n = rec.loan_repayment_months
                if monthly_rate > 0:
                    payment = rec.amount_requested * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
                    rec.loan_total_repayable = payment * n
                else:
                    rec.loan_total_repayable = rec.amount_requested
            else:
                rec.loan_total_repayable = rec.amount_requested

    @api.depends('amount_requested', 'loan_existing_loans')
    def _compute_loan_total_debt(self):
        for rec in self:
            rec.loan_total_debt = rec.amount_requested + (rec.loan_existing_loans or 0.0)

    @api.depends('purchase_line_ids.subtotal')
    def _compute_purchase_total(self):
        for rec in self:
            rec.purchase_total = sum(rec.purchase_line_ids.mapped('subtotal'))

    @api.depends('bill_id')
    def _compute_bill_count(self):
        for rec in self:
            rec.bill_count = 1 if rec.bill_id and rec.bill_id.id else 0

    @api.depends('state', 'requested_by', 'reviewed_by', 'verified_by', 'approved_by')
    def _compute_access_buttons(self):
        user = self.env.user
        is_manager = user.has_group('payment_request.group_payment_request_manager')
        is_finance = user.has_group('payment_request.group_payment_request_finance')
        is_approver = user.has_group('payment_request.group_payment_request_approver')
        for rec in self:
            is_owner = rec.requested_by == user
            rec.can_submit = rec.state == 'draft'
            rec.can_review = rec.state == 'submitted' and is_manager
            rec.can_verify = rec.state == 'reviewed' and is_finance
            rec.can_approve = rec.state == 'verified' and is_approver
            rec.can_reject = rec.state in ('submitted', 'reviewed', 'verified') and (
                is_manager or is_finance or is_approver)
            rec.can_cancel = rec.state in ('draft', 'submitted') and (
                is_owner or is_manager)

    # ── ORM ───────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('payment.request') or _('New')
        return super().create(vals_list)

    @api.onchange('request_type')
    def _onchange_request_type(self):
        self.loan_purpose = False
        self.loan_repayment_months = 0
        self.loan_interest_rate = 0
        self.loan_guarantor = False
        self.advance_month = False
        self.advance_percentage = 0
        self.overtime_hours = 0
        self.overtime_date = False
        self.po_reference = False
        self.expense_category = False
        self.expense_period_from = False
        self.expense_period_to = False

    @api.onchange('employee_id')
    def _onchange_employee_partner(self):
        if self.employee_id and self.employee_id.user_id:
            self.partner_id = self.employee_id.user_id.partner_id

    @api.onchange('overtime_hours', 'overtime_rate')
    def _onchange_overtime(self):
        if self.request_type == 'overtime' and self.overtime_hours and self.overtime_rate:
            self.amount_requested = self.overtime_hours * self.overtime_rate

    @api.onchange('purchase_line_ids')
    def _onchange_purchase_lines(self):
        if self.request_type == 'purchase':
            self.amount_requested = sum(self.purchase_line_ids.mapped('subtotal'))

    # ── Workflow ──────────────────────────────────────────────────────────────────

    def action_submit(self):
        self.ensure_one()
        if not self.amount_requested or self.amount_requested <= 0:
            raise UserError(_('Please enter a valid amount before submitting.'))
        if not self.description:
            raise UserError(_('Please provide a justification before submitting.'))
        if self.request_type == 'loan' and not self.loan_terms_accepted:
            raise UserError(_('The employee must accept the loan terms before submitting.'))
        self.write({'state': 'submitted', 'amount_approved': self.amount_requested})
        self._send_notification_email('submitted')
        return True

    def action_review(self):
        self.ensure_one()
        self.write({
            'state': 'reviewed',
            'reviewed_by': self.env.user.id,
            'date_reviewed': fields.Datetime.now(),
        })
        self._send_notification_email('reviewed')
        return True

    def action_verify(self):
        self.ensure_one()
        self.write({
            'state': 'verified',
            'verified_by': self.env.user.id,
            'date_verified': fields.Datetime.now(),
        })
        self._send_notification_email('verified')
        return True

    def action_approve(self):
        self.ensure_one()
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'date_approved': fields.Datetime.now(),
        })
        self._send_notification_email('approved')
        # Auto-generate bill on approval
        self._generate_bill()
        return True

    def action_reject(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rejection Reason'),
            'res_model': 'payment.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})
        self.message_post(body=_('Request cancelled by %s.') % self.env.user.name)
        return True

    def action_reset_draft(self):
        self.ensure_one()
        self.write({
            'state': 'draft',
            'reviewed_by': False, 'verified_by': False,
            'approved_by': False, 'rejected_by': False,
            'date_reviewed': False, 'date_verified': False,
            'date_approved': False, 'date_rejected': False,
            'rejection_reason': False,
            'manager_note': False, 'finance_note': False, 'approver_note': False,
        })
        self.message_post(body=_('Request reset to draft by %s.') % self.env.user.name)
        return True

    def action_view_bill(self):
        self.ensure_one()
        if not self.bill_id:
            raise UserError(_('No bill has been generated yet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bill'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.bill_id.id,
        }

    def action_print_report(self):
        return self.env.ref('payment_request.action_report_payment_request').report_action(self)

    def action_print_schedule(self):
        return self.env.ref('payment_request.action_report_loan_instalment_schedule').report_action(self)

    def action_print_advance_slip(self):
        return self.env.ref('payment_request.action_report_advance').report_action(self)

    def action_print_overtime_slip(self):
        return self.env.ref('payment_request.action_report_overtime').report_action(self)

    # ── Bill generation ───────────────────────────────────────────────────────────

    def _get_or_create_partner(self):
        """Return partner for the requester. Creates one from employee if needed."""
        self.ensure_one()
        # 1. Use explicitly set partner
        if self.partner_id:
            return self.partner_id
        # 2. Use employee's linked user partner
        if self.employee_id and self.employee_id.user_id:
            partner = self.employee_id.user_id.partner_id
            self.partner_id = partner
            return partner
        # 3. Look for existing partner by employee name
        partner = self.env['res.partner'].search(
            [('name', '=', self.employee_id.name), ('is_company', '=', False)],
            limit=1,
        )
        if partner:
            self.partner_id = partner
            return partner
        # 4. Create new partner from employee
        partner = self.env['res.partner'].create({
            'name': self.employee_id.name,
            'company_type': 'person',
            'is_company': False,
            'company_id': self.company_id.id,
            'comment': _('Auto-created from employee record for payment request %s') % self.name,
        })
        self.partner_id = partner
        self.message_post(
            body=_('Partner <b>%s</b> was auto-created for billing purposes.') % partner.name
        )
        return partner

    def _generate_bill(self):
        """Generate a vendor bill (account.move type=in_invoice) after approval."""
        self.ensure_one()
        if self.bill_id:
            return self.bill_id

        partner = self._get_or_create_partner()

        # Build invoice line name
        type_label = dict(REQUEST_TYPE_SELECTION).get(self.request_type, self.request_type)
        if self.request_type == 'loan':
            purpose_label = dict(LOAN_PURPOSE_SELECTION).get(self.loan_purpose, '')
            line_name = _('Employee Loan — %s — %s') % (self.employee_id.name, purpose_label)
        elif self.request_type == 'advance':
            line_name = _('Salary Advance — %s — %s/%s') % (
                self.employee_id.name,
                self.advance_month or '',
                str(self.advance_year or ''),
            )
        elif self.request_type == 'overtime':
            line_name = _('Overtime Payment — %s — %s hrs on %s') % (
                self.employee_id.name,
                self.overtime_hours,
                self.overtime_date or '',
            )
        elif self.request_type == 'expense':
            expense_label = dict([
                ('travel', 'Travel'), ('accommodation', 'Accommodation'),
                ('meals', 'Meals'), ('communication', 'Communication'),
                ('stationery', 'Stationery'), ('training', 'Training'), ('other', 'Other'),
            ]).get(self.expense_category, '')
            line_name = _('Expense Reimbursement — %s — %s') % (
                self.employee_id.name, expense_label,
            )
        else:
            line_name = _('%s — %s') % (type_label, self.employee_id.name)

        analytic_distribution = (
            {str(self.analytic_account_id.id): 100.0}
            if self.analytic_account_id else False
        )

        # Compose the bill line description from the type label and the
        # request's justification / description.
        line_description = (
            '%s\n%s' % (line_name, self.description) if self.description else line_name
        )

        # Only force the account when one is set; otherwise let Odoo derive the
        # default account from the journal/product on the bill line.
        account_vals = {'account_id': self.account_id.id} if self.account_id else {}

        invoice_line_vals = [(0, 0, {
            'name': line_description,
            'quantity': 1.0,
            'price_unit': self.amount_approved or self.amount_requested,
            'analytic_distribution': analytic_distribution,
            **account_vals,
        })]

        # For purchase requests, create one line per item
        if self.request_type == 'purchase' and self.purchase_line_ids:
            invoice_line_vals = [(0, 0, {
                'name': (
                    '%s\n%s' % (line.description, self.description)
                    if self.description else line.description
                ),
                'quantity': line.quantity,
                'price_unit': line.unit_price,
                'analytic_distribution': analytic_distribution,
                **account_vals,
            }) for line in self.purchase_line_ids]

        move_vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'ref': self.name,
            'narration': self.description,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_line_ids': invoice_line_vals,
        }

        bill = self.env['account.move'].create(move_vals)
        self.bill_id = bill

        self.message_post(
            body=_('Bill <a href="#" data-oe-model="account.move" data-oe-id="%d"><b>%s</b></a> '
                   'was automatically generated after approval.') % (bill.id, bill.name)
        )
        return bill

    # ── Helpers ───────────────────────────────────────────────────────────────────

    def _send_notification_email(self, state):
        template_map = {
            'submitted': 'payment_request.email_template_payment_request_submitted',
            'reviewed': 'payment_request.email_template_payment_request_reviewed',
            'verified': 'payment_request.email_template_payment_request_verified',
            'approved': 'payment_request.email_template_payment_request_approved',
            'rejected': 'payment_request.email_template_payment_request_rejected',
        }
        template_xmlid = template_map.get(state)
        if template_xmlid:
            try:
                template = self.env.ref(template_xmlid)
                template.send_mail(self.id, force_send=False)
            except Exception:
                pass

    def _get_request_type_label(self):
        return dict(REQUEST_TYPE_SELECTION).get(self.request_type, '')

    def _get_state_label(self):
        return dict(STATE_SELECTION).get(self.state, '')
