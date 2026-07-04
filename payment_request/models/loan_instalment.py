from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


INSTALMENT_STATE = [
    ('pending', 'Pending'),
    ('due', 'Due'),
    ('paid', 'Paid'),
    ('overdue', 'Overdue'),
    ('waived', 'Waived'),
]


class LoanInstalment(models.Model):
    _name = 'loan.instalment'
    _description = 'Loan Instalment Schedule'
    _order = 'instalment_no asc'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name',
        store=True,
    )
    loan_id = fields.Many2one(
        'payment.request',
        string='Loan',
        required=True,
        ondelete='cascade',
        domain=[('request_type', '=', 'loan')],
    )
    employee_id = fields.Many2one(
        related='loan_id.employee_id',
        string='Employee',
        store=True,
        readonly=True,
    )
    department_id = fields.Many2one(
        related='loan_id.department_id',
        string='Department',
        store=True,
        readonly=True,
    )
    instalment_no = fields.Integer(string='No.', required=True)
    due_date = fields.Date(string='Due Date', required=True)
    principal_amount = fields.Monetary(
        string='Principal',
        currency_field='currency_id',
    )
    interest_amount = fields.Monetary(
        string='Interest',
        currency_field='currency_id',
    )
    amount = fields.Monetary(
        string='Instalment Amount',
        currency_field='currency_id',
        compute='_compute_amount',
        store=True,
    )
    amount_paid = fields.Monetary(
        string='Amount Paid',
        currency_field='currency_id',
    )
    balance_after = fields.Monetary(
        string='Balance After',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='loan_id.currency_id',
        string='Currency',
        readonly=True,
        store=True,
    )
    state = fields.Selection(
        INSTALMENT_STATE,
        string='Status',
        default='pending',
        required=True,
        tracking=True,
    )
    payment_date = fields.Date(string='Payment Date')
    payment_reference = fields.Char(string='Payment Reference')
    note = fields.Char(string='Note')
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_days_overdue',
        store=False,
    )

    @api.depends('loan_id', 'instalment_no')
    def _compute_display_name(self):
        for rec in self:
            loan_name = rec.loan_id.name if rec.loan_id else ''
            rec.display_name = '%s / Inst. %02d' % (loan_name, rec.instalment_no or 0)

    @api.depends('principal_amount', 'interest_amount')
    def _compute_amount(self):
        for rec in self:
            rec.amount = (rec.principal_amount or 0.0) + (rec.interest_amount or 0.0)

    def _compute_days_overdue(self):
        today = fields.Date.today()
        for rec in self:
            if rec.state == 'overdue' and rec.due_date:
                rec.days_overdue = (today - rec.due_date).days
            else:
                rec.days_overdue = 0

    def action_mark_paid(self):
        for rec in self:
            rec.write({
                'state': 'paid',
                'payment_date': fields.Date.today(),
                'amount_paid': rec.amount,
            })
            rec.loan_id.message_post(
                body=_('Instalment #%d marked as paid on %s.') % (
                    rec.instalment_no, fields.Date.today()
                )
            )

    def action_mark_overdue(self):
        for rec in self:
            if rec.state == 'pending' or rec.state == 'due':
                rec.write({'state': 'overdue'})

    def action_waive(self):
        for rec in self:
            rec.write({'state': 'waived', 'note': 'Waived by %s' % self.env.user.name})

    def action_reset_pending(self):
        for rec in self:
            rec.write({
                'state': 'pending',
                'payment_date': False,
                'amount_paid': 0.0,
                'payment_reference': False,
            })

    @api.model
    def _cron_update_overdue(self):
        """Scheduled action: mark due instalments as overdue."""
        today = fields.Date.today()
        overdue = self.search([
            ('state', 'in', ['pending', 'due']),
            ('due_date', '<', today),
        ])
        overdue.write({'state': 'overdue'})

    def action_view_loan(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.request',
            'view_mode': 'form',
            'res_id': self.loan_id.id,
        }


class PaymentRequestLoanExt(models.Model):
    """Extend payment.request with instalment schedule generation."""
    _inherit = 'payment.request'

    instalment_ids = fields.One2many(
        'loan.instalment',
        'loan_id',
        string='Instalment Schedule',
    )
    instalment_count = fields.Integer(
        string='Instalments',
        compute='_compute_instalment_stats',
        store=False,
    )
    instalments_paid = fields.Integer(
        string='Paid',
        compute='_compute_instalment_stats',
        store=False,
    )
    instalments_overdue = fields.Integer(
        string='Overdue',
        compute='_compute_instalment_stats',
        store=False,
    )
    amount_outstanding = fields.Monetary(
        string='Outstanding Balance',
        currency_field='currency_id',
        compute='_compute_instalment_stats',
        store=False,
    )
    amount_paid_total = fields.Monetary(
        string='Total Paid',
        currency_field='currency_id',
        compute='_compute_instalment_stats',
        store=False,
    )
    loan_completion_pct = fields.Float(
        string='Completion %',
        compute='_compute_instalment_stats',
        store=False,
        digits=(5, 1),
    )

    def _compute_instalment_stats(self):
        for rec in self:
            instalments = rec.instalment_ids
            total = len(instalments)
            paid = instalments.filtered(lambda i: i.state == 'paid')
            overdue = instalments.filtered(lambda i: i.state == 'overdue')
            pending = instalments.filtered(lambda i: i.state in ('pending', 'due', 'overdue'))
            paid_amount = sum(paid.mapped('amount'))
            outstanding = sum(pending.mapped('amount'))
            rec.instalment_count = total
            rec.instalments_paid = len(paid)
            rec.instalments_overdue = len(overdue)
            rec.amount_paid_total = paid_amount
            rec.amount_outstanding = outstanding
            rec.loan_completion_pct = (len(paid) / total * 100) if total else 0.0

    def action_generate_instalments(self):
        """Generate the full instalment schedule for this loan."""
        self.ensure_one()
        if self.request_type != 'loan':
            raise UserError(_('Instalment schedule is only for loan requests.'))
        if not self.loan_repayment_months or self.loan_repayment_months <= 0:
            raise UserError(_('Please set repayment period (months) before generating schedule.'))
        if not self.loan_first_deduction_date:
            raise UserError(_('Please set the first deduction date before generating schedule.'))
        if self.state != 'approved':
            raise UserError(_('Instalment schedule can only be generated for approved loans.'))

        # Clear existing
        self.instalment_ids.unlink()

        n = self.loan_repayment_months
        principal = self.amount_approved or self.amount_requested
        annual_rate = self.loan_interest_rate or 0.0
        monthly_rate = annual_rate / 100.0 / 12.0
        start_date = self.loan_first_deduction_date

        lines = []
        balance = principal

        for i in range(1, n + 1):
            due_date = start_date + relativedelta(months=i - 1)

            if monthly_rate > 0:
                # Amortising schedule (equal payment)
                payment = principal * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
                interest_amt = balance * monthly_rate
                principal_amt = payment - interest_amt
                # Last instalment: absorb rounding
                if i == n:
                    principal_amt = balance
                    payment = principal_amt + interest_amt
            else:
                # Flat equal principal, zero interest
                principal_amt = principal / n
                interest_amt = 0.0
                payment = principal_amt
                # Last instalment: absorb rounding
                if i == n:
                    principal_amt = balance
                    payment = principal_amt

            balance = max(balance - principal_amt, 0.0)

            lines.append({
                'loan_id': self.id,
                'instalment_no': i,
                'due_date': due_date,
                'principal_amount': round(principal_amt, 2),
                'interest_amount': round(interest_amt, 2),
                'balance_after': round(balance, 2),
                'state': 'pending',
            })

        self.env['loan.instalment'].create(lines)
        self.message_post(
            body=_('%d instalment(s) generated for loan %s.') % (n, self.name)
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Instalment Schedule'),
            'res_model': 'loan.instalment',
            'view_mode': 'list,form',
            'domain': [('loan_id', '=', self.id)],
            'context': {'default_loan_id': self.id},
        }

    def action_view_instalments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Instalment Schedule — %s') % self.name,
            'res_model': 'loan.instalment',
            'view_mode': 'list,form',
            'domain': [('loan_id', '=', self.id)],
            'context': {'default_loan_id': self.id},
        }
