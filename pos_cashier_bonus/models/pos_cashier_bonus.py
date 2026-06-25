from datetime import datetime, time

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosCashierBonus(models.Model):
    _name = 'pos.cashier.bonus'
    _description = 'POS Cashier Sales Bonus'
    _inherit = ['mail.thread']
    _order = 'date_from desc, id desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        related='company_id.currency_id', string='Currency', store=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('computed', 'Computed'), ('confirmed', 'Confirmed')],
        string='Status', default='draft', copy=False, tracking=True)

    # --- Period -----------------------------------------------------------
    date_from = fields.Date(
        string='Period Start', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(
        string='Period End', required=True,
        default=lambda self: (
            fields.Date.context_today(self).replace(day=1)
            + relativedelta(months=1, days=-1)))

    # --- Source filters ---------------------------------------------------
    config_ids = fields.Many2many(
        'pos.config', string='POS Registers',
        help="Limit the calculation to these registers. Leave empty for all.")
    group_by = fields.Selection(
        [('employee', 'POS Cashier (Employee)'),
         ('user', 'Salesperson (User)')],
        string='Identify Cashier By', required=True, default='employee',
        help="Employee: the cashier logged on the POS order (multi-employee "
             "mode). User: the order's salesperson / responsible user.")
    sales_basis = fields.Selection(
        [('total', 'Total (tax included)'),
         ('untaxed', 'Untaxed (net of tax)')],
        string='Sales Basis', required=True, default='total',
        help="Which figure of each POS order is counted toward the target.")

    # --- Bonus rule -------------------------------------------------------
    target_per_cashier = fields.Monetary(
        string='Monthly Target / Cashier', required=True, default=26250.0)
    threshold_pct = fields.Float(
        string='Minimum Achievement %', required=True, default=70.0,
        help="Below this achievement percentage, no bonus is paid.")
    bonus_full = fields.Monetary(
        string='Bonus at 100%', required=True, default=100.0,
        help="Bonus earned by a cashier who reaches 100% of target.")
    total_pool = fields.Monetary(
        string='Total Allowance Pool', required=True, default=400.0)
    cap_at_target = fields.Boolean(
        string='Cap Bonus at 100%', default=True,
        help="If set, over-achievement above 100% still pays only the full "
             "bonus. If unset, the bonus scales beyond 100%.")
    redistribute = fields.Boolean(
        string='Redistribute Unused Pool', default=False,
        help="Share the leftover pool equally among cashiers who reached "
             "100% of their target.")
    volume_bonus_amount = fields.Monetary(
        string='Top Order-Volume Bonus', default=30.0,
        help="Extra bonus given to the cashier with the highest number of "
             "POS orders, counted only among cashiers who reached the "
             "minimum achievement threshold. Split equally if cashiers tie. "
             "Paid on top of the allowance pool.")

    # --- Lines & totals ---------------------------------------------------
    line_ids = fields.One2many(
        'pos.cashier.bonus.line', 'bonus_id', string='Cashier Lines')
    total_sales = fields.Monetary(
        compute='_compute_totals', store=True, string='Total POS Sales')
    total_sales_bonus = fields.Monetary(
        compute='_compute_totals', store=True, string='Sales Bonus Total')
    total_volume_bonus = fields.Monetary(
        compute='_compute_totals', store=True, string='Volume Bonus Total')
    total_bonus = fields.Monetary(
        compute='_compute_totals', store=True, string='Total Bonus Payable',
        tracking=True)
    pool_balance = fields.Monetary(
        compute='_compute_totals', store=True, string='Pool Balance')
    pool_overrun = fields.Boolean(
        compute='_compute_totals', store=True, string='Pool Exceeded')

    # --- Accounting -------------------------------------------------------
    journal_id = fields.Many2one(
        'account.journal', string='Bonus Journal',
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_journal(),
        help="Miscellaneous journal in which the bonus accrual is posted.")
    expense_account_id = fields.Many2one(
        'account.account', string='Cashier Bonus Expense Account',
        domain="[('account_type', '=', 'expense'), ('active', '=', True)]",
        default=lambda self: self._default_account('expense_account_id', 'expense'),
        help="Debited on confirmation with the total bonus payable.")
    payable_account_id = fields.Many2one(
        'account.account', string='Bonus Payable Account',
        domain="[('account_type', 'in', ('liability_payable', 'liability_current')),"
               " ('active', '=', True)]",
        default=lambda self: self._default_account('payable_account_id',
                                                   'liability_current'),
        help="Credited on confirmation with the total bonus payable.")
    move_id = fields.Many2one(
        'account.move', string='Journal Entry', readonly=True, copy=False)
    move_state = fields.Selection(
        related='move_id.state', string='Entry Status')

    # --- Cash-control penalty (per cashier) ------------------------------
    cash_diff_tier1 = fields.Float(
        string='Cash Difference - Full Bonus Limit %', required=True,
        default=1.0,
        help="If a cashier's total cash difference (gain plus loss, as "
             "absolute amounts) is within this percentage of their cash "
             "sales, no penalty applies.")
    cash_diff_tier2 = fields.Float(
        string='Cash Difference - Half Bonus Limit %', required=True,
        default=1.5,
        help="Above the full-bonus limit and up to this percentage, half "
             "the bonus is forfeited; beyond it, the whole bonus.")
    total_cash_sales = fields.Monetary(
        compute='_compute_totals', store=True, string='Cash Sales')
    total_cash_gain = fields.Monetary(
        compute='_compute_totals', store=True, string='Cash Difference Gain')
    total_cash_loss = fields.Monetary(
        compute='_compute_totals', store=True, string='Cash Difference Loss')
    total_cash_difference = fields.Monetary(
        compute='_compute_totals', store=True, string='Total Cash Difference')
    cash_penalty_applies = fields.Boolean(
        compute='_compute_totals', store=True, string='Cash Penalty Applied')
    gain_account_id = fields.Many2one(
        'account.account', string='Cash Difference Gain Account',
        related='company_id.cash_diff_gain_account_id', readonly=False,
        help="Account POS closings post cash overages to. Company-wide "
             "setting \u2014 the module reads each session's posted journal "
             "entry for lines on this account.")
    loss_account_id = fields.Many2one(
        'account.account', string='Cash Difference Loss Account',
        related='company_id.cash_diff_loss_account_id', readonly=False,
        help="Account POS closings post cash shortages to. Company-wide "
             "setting \u2014 the module reads each session's posted journal "
             "entry for lines on this account.")

    # ----------------------------------------------------------------------
    def _cash_penalty(self, pct):
        """Tiered forfeit percentage for the combined cash difference."""
        self.ensure_one()
        if pct <= self.cash_diff_tier1:
            return 0.0
        if pct <= self.cash_diff_tier2:
            return 50.0
        return 100.0

    @api.model
    def _default_journal(self):
        last = self.search([('journal_id', '!=', False)], limit=1)
        if last:
            return last.journal_id
        return self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.env.company.id)],
            limit=1)

    @api.model
    def _default_account(self, field, account_type):
        last = self.search([(field, '!=', False)], limit=1)
        if last:
            return last[field]
        return self.env['account.account'].search(
            [('account_type', '=', account_type), ('active', '=', True)],
            limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pos.cashier.bonus') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids.sales_bonus', 'line_ids.volume_bonus',
                 'line_ids.bonus_amount', 'line_ids.actual_sales',
                 'line_ids.cash_sales', 'line_ids.cash_gain',
                 'line_ids.cash_loss', 'line_ids.cash_penalty_pct', 'total_pool')
    def _compute_totals(self):
        for rec in self:
            rec.total_sales = sum(rec.line_ids.mapped('actual_sales'))
            rec.total_sales_bonus = sum(rec.line_ids.mapped('sales_bonus'))
            rec.total_volume_bonus = sum(rec.line_ids.mapped('volume_bonus'))
            rec.total_bonus = sum(rec.line_ids.mapped('bonus_amount'))
            rec.pool_balance = rec.total_pool - rec.total_sales_bonus
            rec.pool_overrun = rec.total_sales_bonus > rec.total_pool
            rec.total_cash_sales = sum(rec.line_ids.mapped('cash_sales'))
            rec.total_cash_gain = sum(rec.line_ids.mapped('cash_gain'))
            rec.total_cash_loss = sum(rec.line_ids.mapped('cash_loss'))
            rec.total_cash_difference = rec.total_cash_gain + rec.total_cash_loss
            rec.cash_penalty_applies = any(
                p > 0 for p in rec.line_ids.mapped('cash_penalty_pct'))

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from and (not self.date_to or self.date_to < self.date_from):
            self.date_to = self.date_from + relativedelta(months=1, days=-1)

    # --- Actions ----------------------------------------------------------
    def action_compute(self):
        """Pull POS sales and per-cashier cash data, then recompute bonuses."""
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("Period Start cannot be after Period End."))
        if self.target_per_cashier <= 0:
            raise UserError(_("Monthly Target per cashier must be greater than zero."))

        employee_mode = self.group_by == 'employee'
        start = datetime.combine(self.date_from, time.min)
        end = datetime.combine(self.date_to, time.max)
        domain = [
            ('company_id', '=', self.company_id.id),
            ('date_order', '>=', start),
            ('date_order', '<=', end),
            # Only orders that have reached the posted ledger: 'done' is the
            # POS "Posted" state, 'invoiced' has been posted via its invoice.
            # Draft and paid-but-not-yet-posted orders are excluded.
            ('state', 'in', ('done', 'invoiced')),
        ]
        if self.config_ids:
            domain.append(('session_id.config_id', 'in', self.config_ids.ids))

        # Sales, order counts and the cashier/session of each order.
        
        orders_data = self.env['pos.order'].search_read(
            domain, ['user_id', 'session_id', 'amount_total', 'amount_tax'])
        sales, counts, order_cashier = {}, {}, {}
        order_ids, session_ids = [], set()

        if employee_mode:
            session_map = {}
            for od in orders_data:
                if od['session_id']:
                    session_ids.add(od['session_id'][0])
            for sess in self.env['pos.session'].browse(list(session_ids)):
                emp_id = sess.user_id.employee_id.id or False
                session_map[sess.id] = emp_id
            for od in orders_data:
                order_ids.append(od['id'])
                cid = session_map.get(od['session_id'][0], False) if od['session_id'] else False
                order_cashier[od['id']] = cid
                if not cid:
                    continue
                amount = (od['amount_total'] - od['amount_tax']
                          if self.sales_basis == 'untaxed' else od['amount_total'])
                sales[cid] = sales.get(cid, 0.0) + amount
                counts[cid] = counts.get(cid, 0) + 1
        else:
            for od in orders_data:
                order_ids.append(od['id'])
                cid = od['user_id'][0] if od['user_id'] else False
                order_cashier[od['id']] = cid
                if od['session_id']:
                    session_ids.add(od['session_id'][0])
                if not cid:
                    continue
                amount = (od['amount_total'] - od['amount_tax']
                          if self.sales_basis == 'untaxed' else od['amount_total'])
                sales[cid] = sales.get(cid, 0.0) + amount
                counts[cid] = counts.get(cid, 0) + 1

        # Cash throughput per cashier: total of all POS payments, across
        # every payment method (in this configuration they are bank
        # journals). Used as the base for the cash-difference percentage.
        cash_sales = {}
        if order_ids:
            cash_pay = self.env['pos.payment']._read_group(
                [('pos_order_id', 'in', order_ids)],
                groupby=['pos_order_id'], aggregates=['amount:sum'])
            for order, amount in cash_pay:
                cid = order_cashier.get(order.id)
                if cid:
                    cash_sales[cid] = cash_sales.get(cid, 0.0) + (amount or 0.0)

        # Cash difference per cashier, split into gain and loss. The closing
        # difference of each session is read from its posted journal entry
        # (the lines on the bank journal's Cash Difference Gain / Loss
        # accounts) and attributed to the cashier responsible for the
        # session.
        gain, loss = {}, {}
        for sess in self.env['pos.session'].browse(list(session_ids)):
            if sess.state != 'closed':
                continue
            cid = (sess.user_id.employee_id.id if employee_mode
                   else sess.user_id.id)
            if not cid:
                continue
            diff = sess.cash_difference_amount
            if diff > 0:
                gain[cid] = gain.get(cid, 0.0) + diff
            elif diff < 0:
                loss[cid] = loss.get(cid, 0.0) - diff

        # Build / refresh one line per cashier.
        Line = self.env['pos.cashier.bonus.line']
        all_cids = (set(sales) | set(counts) | set(cash_sales)
                    | set(gain) | set(loss))
        all_cids.discard(False)
        existing = {}
        for line in self.line_ids:
            cid = (line.employee_id if employee_mode else line.user_id).id
            existing[cid] = line
        for cid in all_cids:
            vals = {
                'actual_sales': sales.get(cid, 0.0),
                'order_count': counts.get(cid, 0),
                'cash_sales': cash_sales.get(cid, 0.0),
                'cash_gain': gain.get(cid, 0.0),
                'cash_loss': loss.get(cid, 0.0),
            }
            if cid in existing:
                existing[cid].write(vals)
            else:
                vals['bonus_id'] = self.id
                vals['target'] = self.target_per_cashier
                vals['employee_id' if employee_mode else 'user_id'] = cid
                Line.create(vals)
        for cid, line in existing.items():
            if cid not in all_cids:
                line.write({'actual_sales': 0.0, 'order_count': 0,
                            'cash_sales': 0.0, 'cash_gain': 0.0,
                            'cash_loss': 0.0})

        self._apply_bonus()
        self.state = 'computed'
        return True

    def _apply_bonus(self):
        """Apply the bonus rule to every line of each record."""
        for rec in self:
            full_achievers = self.env['pos.cashier.bonus.line']
            for line in rec.line_ids:
                target = line.target or rec.target_per_cashier
                pct = (line.actual_sales / target * 100.0) if target else 0.0
                line.achievement_pct = pct
                if pct < rec.threshold_pct:
                    base = 0.0
                elif rec.cap_at_target:
                    base = min(pct, 100.0) / 100.0 * rec.bonus_full
                else:
                    base = pct / 100.0 * rec.bonus_full
                line.bonus_base = base
                line.sales_bonus = base
                line.volume_bonus = 0.0
                line.is_top_volume = False
                if pct >= 100.0:
                    full_achievers |= line

            # Optional redistribution of the unused pool to target achievers.
            if rec.redistribute and full_achievers:
                leftover = rec.total_pool - sum(rec.line_ids.mapped('bonus_base'))
                if leftover > 0:
                    share = leftover / len(full_achievers)
                    for line in full_achievers:
                        line.sales_bonus = line.bonus_base + share

            # Order-volume bonus: only cashiers who reached the minimum
            # achievement threshold are eligible. Among those, the highest
            # order count wins (split equally on a tie).
            if rec.volume_bonus_amount:
                eligible = rec.line_ids.filtered(
                    lambda l: l.achievement_pct >= rec.threshold_pct)
                top_count = max(eligible.mapped('order_count'), default=0)
                if top_count > 0:
                    winners = eligible.filtered(
                        lambda l: l.order_count == top_count)
                    share = rec.volume_bonus_amount / len(winners)
                    for line in winners:
                        line.is_top_volume = True
                        line.volume_bonus = share

            # Cash-control penalty, per cashier. Cash gain and cash loss are
            # added as absolute amounts into one total cash difference; the
            # tier rule is read once against that combined figure.
            for line in rec.line_ids:
                cs = line.cash_sales
                line.cash_difference = line.cash_gain + line.cash_loss
                line.cash_diff_pct = (line.cash_difference / cs * 100.0
                                      if cs > 0 else 0.0)
                line.cash_penalty_pct = rec._cash_penalty(line.cash_diff_pct)
                gross = line.sales_bonus + line.volume_bonus
                line.bonus_amount = gross * (100.0 - line.cash_penalty_pct) / 100.0

    # --- Accounting posting ----------------------------------------------
    def _prepare_bonus_move_vals(self):
        """Build the journal entry: debit expense, credit payable."""
        self.ensure_one()
        amount = self.company_id.currency_id.round(self.total_bonus)
        return {
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.date_to,
            'ref': _("Cashier Bonus %s", self.name),
            'company_id': self.company_id.id,
            'line_ids': [
                (0, 0, {
                    'name': _("Cashier bonus expense (%s)", self.name),
                    'account_id': self.expense_account_id.id,
                    'debit': amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': _("Bonus payable (%s)", self.name),
                    'account_id': self.payable_account_id.id,
                    'debit': 0.0,
                    'credit': amount,
                }),
            ],
        }

    def _create_bonus_move(self):
        """Create and post the bonus accrual entry for one record."""
        self.ensure_one()
        if self.move_id or self.company_id.currency_id.is_zero(self.total_bonus):
            return self.move_id
        if not (self.journal_id and self.expense_account_id
                and self.payable_account_id):
            raise UserError(_(
                "Set the Bonus Journal, Cashier Bonus Expense Account and "
                "Bonus Payable Account before confirming."))
        move = self.env['account.move'].create(self._prepare_bonus_move_vals())
        move.action_post()
        self.move_id = move.id
        self.message_post(body=_(
            "Bonus confirmed. %(amt)s posted \u2014 debit %(exp)s, "
            "credit %(pay)s (entry %(move)s).",
            amt=self.total_bonus,
            exp=self.expense_account_id.display_name,
            pay=self.payable_account_id.display_name,
            move=move.name))
        return move

    def action_view_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Bonus Journal Entry"),
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # --- Workflow ---------------------------------------------------------
    def action_confirm(self):
        for rec in self:
            if rec.state != 'computed':
                raise UserError(_("Compute the bonus before confirming it."))
            rec._create_bonus_move()
            rec.state = 'confirmed'

    def action_reset(self):
        for rec in self:
            move = rec.move_id
            if move and move.state == 'posted':
                move._reverse_moves([{
                    'date': fields.Date.context_today(rec),
                    'ref': _("Reversal of %s", move.name),
                }], cancel=True)
                rec.message_post(body=_(
                    "Reset to draft \u2014 journal entry %s reversed.",
                    move.name))
            elif move:
                move.unlink()
            rec.move_id = False
            rec.state = 'draft'


class PosCashierBonusLine(models.Model):
    _name = 'pos.cashier.bonus.line'
    _description = 'POS Cashier Bonus Line'
    _order = 'achievement_pct desc'

    bonus_id = fields.Many2one(
        'pos.cashier.bonus', string='Bonus Run', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='bonus_id.company_id', store=True)
    currency_id = fields.Many2one(related='bonus_id.currency_id', store=True)
    group_by = fields.Selection(related='bonus_id.group_by')
    threshold_pct = fields.Float(related='bonus_id.threshold_pct')

    employee_id = fields.Many2one('hr.employee', string='Cashier (Employee)')
    user_id = fields.Many2one('res.users', string='Salesperson')
    cashier_name = fields.Char(
        compute='_compute_cashier_name', store=True, string='Cashier')

    order_count = fields.Integer(string='POS Orders')
    target = fields.Monetary(string='Target', default=0.0)
    actual_sales = fields.Monetary(string='Actual POS Sales')
    achievement_pct = fields.Float(string='Achievement %', digits=(16, 2))
    bonus_base = fields.Monetary(string='Base Bonus')
    sales_bonus = fields.Monetary(string='Sales Bonus')
    volume_bonus = fields.Monetary(string='Volume Bonus')
    is_top_volume = fields.Boolean(string='Top Order Volume')
    cash_sales = fields.Monetary(string='Cash Sales')
    cash_gain = fields.Monetary(string='Cash Difference Gain')
    cash_loss = fields.Monetary(string='Cash Difference Loss')
    cash_difference = fields.Monetary(
        string='Total Cash Difference',
        help="Cash gain plus cash loss, taken as absolute amounts.")
    cash_diff_pct = fields.Float(string='Cash Difference %', digits=(16, 2))
    cash_penalty_pct = fields.Float(string='Bonus Forfeited %')
    bonus_amount = fields.Monetary(string='Bonus Payable')
    status_label = fields.Char(compute='_compute_status_label', string='Status')

    @api.depends('employee_id', 'user_id')
    def _compute_cashier_name(self):
        for line in self:
            line.cashier_name = (
                line.employee_id.name or line.user_id.name or _('Unassigned'))

    @api.depends('achievement_pct', 'threshold_pct')
    def _compute_status_label(self):
        for line in self:
            if line.achievement_pct >= 100.0:
                line.status_label = _('Target met')
            elif line.achievement_pct >= line.threshold_pct:
                line.status_label = _('Partial bonus')
            else:
                line.status_label = _('Below threshold')