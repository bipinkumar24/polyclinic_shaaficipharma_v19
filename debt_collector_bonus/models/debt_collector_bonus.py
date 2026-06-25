from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


# Speed-factor day-band upper bounds, in days from due date to collection.
# A payment collected within BAND_1 days earns speed_factor_1, within BAND_2
# earns speed_factor_2, and so on; anything slower earns speed_factor_5.
SPEED_BANDS = (7, 30, 60, 90)


class DebtCollectorBonus(models.Model):
    _name = 'debt.collector.bonus'
    _description = 'Debt Collector Incentive Bonus'
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
        [('draft', 'Draft'), ('computed', 'Computed'),
         ('confirmed', 'Confirmed')],
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

    # --- Scheme parameters (all configurable) -----------------------------
    aged_threshold_days = fields.Integer(
        string='Aged-Debt Threshold (days)', required=True, default=30,
        help="A debt counts toward the eligibility gate only if its invoice "
             "was older than this many days at the start of the period.")
    gate_pct = fields.Float(
        string='Eligibility Gate %', required=True, default=75.0,
        help="A collector earns no bonus unless they recover more than this "
             "percentage of their opening aged-debt book.")
    upper_pct = fields.Float(
        string='Upper Band %', required=True, default=90.0,
        help="At or above this recovery percentage the collector earns the "
             "full pool share plus the over-performance kicker.")
    pool_pct = fields.Float(
        string='Pool Funding %', required=True, default=2.5,
        help="The bonus pool is this percentage of total net reconciled "
             "recovery for the period.")
    kicker_mode = fields.Selection(
        [('points', 'Uplift on base bonus (%)'),
         ('fixed', 'Fixed top-up amount')],
        string='Kicker Type', required=True, default='points',
        help="How the over-performance kicker (paid above the upper band) "
             "is calculated.")
    kicker_value = fields.Float(
        string='Kicker Value', required=True, default=20.0,
        help="For an uplift kicker, the percentage added to the base bonus. "
             "For a fixed kicker, the flat amount added.")
    speed_factor_1 = fields.Float(
        string='Speed Factor <=7 days', required=True, default=1.5)
    speed_factor_2 = fields.Float(
        string='Speed Factor 8-30 days', required=True, default=1.2)
    speed_factor_3 = fields.Float(
        string='Speed Factor 31-60 days', required=True, default=1.0)
    speed_factor_4 = fields.Float(
        string='Speed Factor 61-90 days', required=True, default=0.85)
    speed_factor_5 = fields.Float(
        string='Speed Factor 90+ days', required=True, default=0.7)
    clawback = fields.Boolean(
        string='Clawback Reversed Payments', default=True,
        help="Exclude any payment whose journal entry has been reversed, so "
             "bounced or cancelled receipts earn no bonus.")
    excluded_partner_ids = fields.Many2many(
        'res.partner', string='Hardship / Excluded Accounts',
        help="Customers under a genuine-hardship hold. Their debt and any "
             "recovery against it are left out of the scheme entirely.")

    # --- Accounting -------------------------------------------------------
    journal_id = fields.Many2one(
        'account.journal', string='Bonus Journal',
        domain="[('type', '=', 'general')]")
    expense_account_id = fields.Many2one(
        'account.account', string='Bonus Expense Account')
    payable_account_id = fields.Many2one(
        'account.account', string='Bonus Payable Account')
    move_id = fields.Many2one(
        'account.move', string='Journal Entry', readonly=True, copy=False)

    # --- Lines & totals ---------------------------------------------------
    line_ids = fields.One2many(
        'debt.collector.bonus.line', 'bonus_id', string='Collector Lines')
    total_recovered = fields.Monetary(
        compute='_compute_totals', store=True, string='Total Recovered')
    total_pool = fields.Monetary(
        compute='_compute_totals', store=True, string='Bonus Pool')
    total_bonus = fields.Monetary(
        compute='_compute_totals', store=True, string='Total Bonus Payable',
        tracking=True)

    @api.depends('line_ids.total_recovered', 'line_ids.bonus_amount',
                 'pool_pct')
    def _compute_totals(self):
        for rec in self:
            recovered = sum(rec.line_ids.mapped('total_recovered'))
            rec.total_recovered = recovered
            rec.total_pool = recovered * rec.pool_pct / 100.0
            rec.total_bonus = sum(rec.line_ids.mapped('bonus_amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'debt.collector.bonus') or _('New')
        return super().create(vals_list)

    @api.constrains('date_from', 'date_to')
    def _check_period(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_("Period Start must precede Period End."))

    # --- Speed factor -----------------------------------------------------
    def _speed_factor(self, days):
        """Return the speed multiplier for a recovery collected `days` days
        after the invoice fell due (negative means collected early)."""
        self.ensure_one()
        if days <= SPEED_BANDS[0]:
            return self.speed_factor_1
        if days <= SPEED_BANDS[1]:
            return self.speed_factor_2
        if days <= SPEED_BANDS[2]:
            return self.speed_factor_3
        if days <= SPEED_BANDS[3]:
            return self.speed_factor_4
        return self.speed_factor_5

    # --- Data gathering ---------------------------------------------------
    def _line_due_date(self, move_line):
        """Best available due date for a receivable line."""
        return (move_line.date_maturity
                or move_line.move_id.invoice_date_due
                or move_line.date)

    def _opening_residual(self, inv_line):
        """Residual of a receivable invoice line as it stood at period start:
        the current residual plus every amount reconciled on or after the
        period start added back."""
        self.ensure_one()
        residual = abs(inv_line.amount_residual)
        for partial in inv_line.matched_credit_ids:
            if partial.max_date and partial.max_date >= self.date_from:
                residual += partial.amount
        return residual

    def _collector_of_record(self, partner, cache):
        """The user who most recently recorded a customer payment for this
        partner \u2014 preferring activity before the period start. Returns a
        res.users or empty recordset (unassigned)."""
        self.ensure_one()
        if partner.id in cache:
            return cache[partner.id]
        Payment = self.env['account.payment']
        base = [('partner_id', '=', partner.id),
                ('partner_type', '=', 'customer'),
                ('payment_type', '=', 'inbound')]
        pay = Payment.search(
            base + [('date', '<', self.date_from)], order='date desc, id desc',
            limit=1)
        if not pay:
            pay = Payment.search(base, order='date desc, id desc', limit=1)
        user = pay.create_uid if pay else self.env['res.users']
        cache[partner.id] = user
        return user

    def _is_reversed(self, move):
        """True if `move` has a posted reversal entry. The reversal One2many
        has been named differently across Odoo versions, so resolve it from
        the model's fields rather than assuming a name."""
        for fname in ('reversal_move_ids', 'reversal_move_id'):
            if fname in move._fields:
                revs = move[fname]
                return bool(revs.filtered(lambda m: m.state == 'posted'))
        return False

    def _period_payments(self):
        """Posted inbound customer payments recorded inside the period,
        honouring the clawback and hardship settings."""
        self.ensure_one()
        domain = [('partner_type', '=', 'customer'),
                  ('payment_type', '=', 'inbound'),
                  ('date', '>=', self.date_from),
                  ('date', '<=', self.date_to),
                  ('company_id', '=', self.company_id.id)]
        payments = self.env['account.payment'].search(domain)
        result = self.env['account.payment']
        for pay in payments:
            move = pay.move_id
            if not move or move.state != 'posted':
                continue
            if pay.partner_id in self.excluded_partner_ids:
                continue
            if self.clawback and self._is_reversed(move):
                continue
            result |= pay
        return result

    # --- Compute ----------------------------------------------------------
    def action_compute(self):
        self.ensure_one()
        if self.state == 'confirmed':
            raise UserError(_("Reset the bonus to draft before recomputing."))
        Line = self.env['debt.collector.bonus.line']
        threshold = self.aged_threshold_days
        cutoff = self.date_from - timedelta(days=threshold)
        rec_cache = {}

        # 1) Opening aged-debt book, attributed to a collector of record.
        opening = {}  # user_id -> opening aged residual
        aged_lines = self.env['account.move.line'].search([
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('debit', '>', 0.0),
            ('date_maturity', '!=', False),
            ('date_maturity', '<', cutoff),
            ('company_id', '=', self.company_id.id)])
        for ml in aged_lines:
            partner = ml.partner_id
            if not partner or partner in self.excluded_partner_ids:
                continue
            residual = self._opening_residual(ml)
            if residual <= 0.0:
                continue
            user = self._collector_of_record(partner, rec_cache)
            if not user:
                continue
            opening[user.id] = opening.get(user.id, 0.0) + residual

        # 2) Recovery and speed points from the period's payments.
        recovered = {}        # user_id -> total reconciled recovery
        recovered_aged = {}   # user_id -> recovery against aged debt
        points = {}           # user_id -> speed-weighted points
        for pay in self._period_payments():
            user = pay.create_uid
            if not user:
                continue
            for ml in pay.move_id.line_ids:
                if ml.account_id.account_type != 'asset_receivable':
                    continue
                for partial in ml.matched_debit_ids:
                    inv_line = partial.debit_move_id
                    amount = partial.amount
                    if amount <= 0.0:
                        continue
                    if inv_line.partner_id in self.excluded_partner_ids:
                        continue
                    due = self._line_due_date(inv_line)
                    recovered[user.id] = recovered.get(user.id, 0.0) + amount
                    if due:
                        speed_days = (pay.date - due).days
                        factor = self._speed_factor(speed_days)
                        if (self.date_from - due).days > threshold:
                            recovered_aged[user.id] = recovered_aged.get(
                                user.id, 0.0) + amount
                    else:
                        factor = self.speed_factor_3
                    points[user.id] = points.get(
                        user.id, 0.0) + amount * factor

        # 3) Write one line per collector seen on either side.
        user_ids = set(opening) | set(recovered) | set(points)
        existing = {l.user_id.id: l for l in self.line_ids}
        for uid in user_ids:
            vals = {
                'opening_aged_debt': opening.get(uid, 0.0),
                'recovered_aged': recovered_aged.get(uid, 0.0),
                'total_recovered': recovered.get(uid, 0.0),
                'points': points.get(uid, 0.0),
            }
            if uid in existing:
                existing[uid].write(vals)
            else:
                vals['bonus_id'] = self.id
                vals['user_id'] = uid
                Line.create(vals)
        for uid, line in existing.items():
            if uid not in user_ids:
                line.write({'opening_aged_debt': 0.0, 'recovered_aged': 0.0,
                            'total_recovered': 0.0, 'points': 0.0})

        self._apply_scheme()
        self.state = 'computed'
        return True

    def _apply_scheme(self):
        """Apply the gate, the two-band payout and the kicker to every line."""
        for rec in self:
            # Gate and band factor.
            for line in rec.line_ids:
                opening = line.opening_aged_debt
                pct = (line.recovered_aged / opening * 100.0
                       if opening > 0.0 else 0.0)
                line.gate_achievement_pct = pct
                line.eligible = opening > 0.0 and pct > rec.gate_pct
                if not line.eligible:
                    line.band_factor = 0.0
                elif pct >= rec.upper_pct:
                    line.band_factor = 1.0
                else:
                    span = rec.upper_pct - rec.gate_pct
                    line.band_factor = ((pct - rec.gate_pct) / span
                                        if span > 0.0 else 1.0)

            # Pool split among eligible collectors, weighted by points.
            pool = rec.total_recovered * rec.pool_pct / 100.0
            eligible = rec.line_ids.filtered('eligible')
            total_pts = sum(eligible.mapped('points'))
            for line in rec.line_ids:
                if not line.eligible or total_pts <= 0.0:
                    line.base_bonus = 0.0
                    line.kicker_bonus = 0.0
                    continue
                line.base_bonus = (pool * line.points / total_pts
                                   * line.band_factor)
                if line.gate_achievement_pct >= rec.upper_pct:
                    if rec.kicker_mode == 'points':
                        line.kicker_bonus = (line.base_bonus
                                             * rec.kicker_value / 100.0)
                    else:
                        line.kicker_bonus = rec.kicker_value
                else:
                    line.kicker_bonus = 0.0

    # --- Accounting posting ----------------------------------------------
    def _prepare_bonus_move_vals(self):
        self.ensure_one()
        amount = self.company_id.currency_id.round(self.total_bonus)
        return {
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.date_to,
            'ref': _("Debt Collector Bonus %s", self.name),
            'company_id': self.company_id.id,
            'line_ids': [
                (0, 0, {
                    'name': _("Debt collector bonus expense (%s)", self.name),
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
        self.ensure_one()
        if self.move_id or self.company_id.currency_id.is_zero(
                self.total_bonus):
            return self.move_id
        if not (self.journal_id and self.expense_account_id
                and self.payable_account_id):
            raise UserError(_(
                "Set the Bonus Journal, Bonus Expense Account and Bonus "
                "Payable Account before confirming."))
        move = self.env['account.move'].create(
            self._prepare_bonus_move_vals())
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


class DebtCollectorBonusLine(models.Model):
    _name = 'debt.collector.bonus.line'
    _description = 'Debt Collector Bonus Line'
    _order = 'gate_achievement_pct desc'

    bonus_id = fields.Many2one(
        'debt.collector.bonus', string='Bonus Run', required=True,
        ondelete='cascade')
    company_id = fields.Many2one(related='bonus_id.company_id', store=True)
    currency_id = fields.Many2one(related='bonus_id.currency_id', store=True)
    gate_pct = fields.Float(related='bonus_id.gate_pct')
    upper_pct = fields.Float(related='bonus_id.upper_pct')

    user_id = fields.Many2one(
        'res.users', string='Collector', required=True)

    opening_aged_debt = fields.Monetary(
        string='Opening Aged Debt',
        help="Debt aged over the threshold, in this collector's opening "
             "book, outstanding at the start of the period.")
    recovered_aged = fields.Monetary(
        string='Aged Debt Recovered',
        help="Recovery in the period that settled aged debt.")
    total_recovered = fields.Monetary(
        string='Total Recovered',
        help="All reconciled customer recovery the collector recorded.")
    points = fields.Float(
        string='Speed Points', digits=(16, 2),
        help="Recovery weighted by the speed factor of each payment.")

    gate_achievement_pct = fields.Float(
        string='Aged Recovery %', digits=(16, 2))
    eligible = fields.Boolean(string='Passed Gate')
    band_factor = fields.Float(string='Band Factor', digits=(16, 4))
    base_bonus = fields.Monetary(string='Base Bonus')
    kicker_bonus = fields.Monetary(string='Kicker')
    conduct_penalty_pct = fields.Float(
        string='Conduct Penalty %', default=0.0,
        help="Share of the bonus forfeited for a verified conduct or "
             "harassment complaint. Set by the manager before confirming.")
    bonus_amount = fields.Monetary(
        string='Bonus Payable', compute='_compute_bonus_amount', store=True)
    status_label = fields.Char(
        compute='_compute_status_label', string='Status')

    @api.depends('base_bonus', 'kicker_bonus', 'conduct_penalty_pct')
    def _compute_bonus_amount(self):
        for line in self:
            gross = line.base_bonus + line.kicker_bonus
            penalty = max(0.0, min(line.conduct_penalty_pct, 100.0))
            amount = gross * (100.0 - penalty) / 100.0
            line.bonus_amount = (line.currency_id.round(amount)
                                 if line.currency_id else amount)

    @api.depends('eligible', 'gate_achievement_pct', 'upper_pct', 'gate_pct')
    def _compute_status_label(self):
        for line in self:
            if not line.eligible:
                line.status_label = _('Below gate')
            elif line.gate_achievement_pct >= line.upper_pct:
                line.status_label = _('Over-performance')
            else:
                line.status_label = _('In band')
