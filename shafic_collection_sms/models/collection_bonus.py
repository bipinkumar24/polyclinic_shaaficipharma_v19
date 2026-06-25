# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


def _g(value):
    """Compact number formatting: 1000.0 -> '1000', 2.5 -> '2.5'."""
    return ('%f' % (value or 0.0)).rstrip('0').rstrip('.') or '0'


def _compute_tier_bonus(tiers, total, calc_mode):
    """Run a collected total through a tier recordset.

    Returns (bonus_total, [breakdown dicts]). Works for the shared rule
    tiers and for a single cashier's own tiers alike.
    """
    tiers = tiers.sorted(key=lambda t: t.from_amount)
    bonus = 0.0
    rows = []
    if not tiers:
        return 0.0, rows
    if calc_mode == 'flat_tier':
        chosen = False
        for t in tiers:
            if total >= t.from_amount:
                chosen = t
        if chosen:
            b = total * chosen.percent / 100.0
            bonus = b
            rows.append({
                'name': chosen.name, 'from_amount': chosen.from_amount,
                'to_amount': chosen.to_amount, 'percent': chosen.percent,
                'base_amount': total, 'bonus_amount': b,
            })
    else:  # marginal brackets
        for t in tiers:
            lower = t.from_amount
            upper = t.to_amount or None
            if total <= lower:
                continue
            seg_top = total if upper is None else min(total, upper)
            base = seg_top - lower
            if base <= 0:
                continue
            b = base * t.percent / 100.0
            bonus += b
            rows.append({
                'name': t.name, 'from_amount': lower,
                'to_amount': t.to_amount, 'percent': t.percent,
                'base_amount': base, 'bonus_amount': b,
            })
    return bonus, rows


class CollectionBonusConfig(models.Model):
    _name = 'collection.bonus.config'
    _description = 'Collection Bonus Rule'
    _order = 'company_id, name'

    name = fields.Char(required=True, default='Collection Bonus Rule')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Branch / Company', required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    scope = fields.Selection(
        [('single', 'Single collector'),
         ('cashier', 'Per cashier')],
        string='Bonus Scope', default='single', required=True,
        help="Single collector: all collections in the period are credited to "
             "one person. Per cashier: collections are split per cashier and "
             "the bonus is worked out for each on their own collections.")
    cashier_attribution = fields.Selection(
        [('user', 'By recording user (who created the entry)'),
         ('journal', 'By journal (each cashier owns journals)')],
        string='Attribute Payments', default='user', required=True,
        help="How each payment is credited to a cashier under 'Per cashier' "
             "scope. By recording user: the Odoo login that created the entry "
             "- only splits cashiers if each logs in separately. By journal: "
             "each payment goes to the cashier who owns its journal (a cashier "
             "can own several journals) - use this when everyone records under "
             "one login but uses different tills/journals.")
    collector_user_id = fields.Many2one(
        'res.users', string='Collector',
        help="The single person credited with all collections under this rule "
             "(used when scope is 'Single collector').",
    )
    calc_mode = fields.Selection(
        [('marginal', 'Bracket tiers (each band paid at its own rate)'),
         ('flat_tier', 'Whole amount at the highest tier reached')],
        string='Calculation Mode', default='marginal', required=True,
        help="Bracket tiers: like tax bands - the first band of collections "
             "earns its rate, the next band its rate, and so on (no cliff "
             "edge). Whole amount: the entire collected total is paid at the "
             "rate of the highest tier whose 'From' is reached.",
    )
    tier_ids = fields.One2many(
        'collection.bonus.tier', 'config_id',
        string='Tiers',
        help="Shared/default tier table. Used for 'Single collector', and as "
             "the fall-back for any cashier who has no tiers of their own.")
    cashier_ids = fields.One2many(
        'collection.bonus.cashier', 'config_id', string='Cashiers',
        help="Per-cashier tier tables (scope 'Per cashier'). A cashier with no "
             "tiers here falls back to the shared tier table above.")
    excluded_journal_ids = fields.Many2many(
        'account.journal', string='Excluded Journals',
        help="Payments posted in these journals are NOT counted as collections "
             "- e.g. the POS 'Daily Cash Sales' / session-closing journals. "
             "Genuine customer payments carry a customer and are always counted; "
             "POS aggregate entries usually have no customer and are skipped "
             "already, but listing their journals here makes it certain.")
    collector_journal_ids = fields.Many2many(
        'account.journal',
        relation='collection_bonus_collector_journal_rel',
        column1='config_id', column2='journal_id',
        string="Collector's Journals",
        help="Single-collector scope only: base the bonus on collections in "
             "THESE journals (the collector's own tills / mobile-money "
             "accounts). Leave empty to count every collection in the period.")

    @api.depends('name', 'company_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.company_id:
                rec.display_name = '%s (%s)' % (rec.name, rec.company_id.name)
            else:
                rec.display_name = rec.name or ''


class CollectionBonusTier(models.Model):
    _name = 'collection.bonus.tier'
    _description = 'Collection Bonus Tier'
    _order = 'from_amount, id'

    config_id = fields.Many2one(
        'collection.bonus.config', ondelete='cascade')
    cashier_id = fields.Many2one(
        'collection.bonus.cashier', ondelete='cascade',
        help="Set when this tier belongs to a specific cashier's table.")
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id')
    from_amount = fields.Monetary(
        string='From', required=True, default=0.0,
        help="Lower bound of this band (inclusive).")
    to_amount = fields.Monetary(
        string='To', default=0.0,
        help="Upper bound of this band. Leave 0 for the top band (no limit).")
    percent = fields.Float(string='Rate (%)', required=True, default=0.0)
    name = fields.Char(compute='_compute_name')

    @api.depends('config_id.currency_id', 'cashier_id.config_id.currency_id')
    def _compute_currency_id(self):
        for t in self:
            cfg = t.config_id or t.cashier_id.config_id
            t.currency_id = cfg.currency_id if cfg else self.env.company.currency_id

    @api.constrains('config_id', 'cashier_id')
    def _check_parent(self):
        for t in self:
            if not t.config_id and not t.cashier_id:
                raise ValidationError(_(
                    "A tier must belong to a bonus rule or a cashier."))

    @api.depends('from_amount', 'to_amount', 'percent')
    def _compute_name(self):
        for t in self:
            hi = 'and up' if not t.to_amount else _g(t.to_amount)
            t.name = '%s - %s @ %s%%' % (_g(t.from_amount), hi, _g(t.percent))

    @api.constrains('from_amount', 'to_amount', 'percent')
    def _check_tier(self):
        for t in self:
            if t.percent < 0:
                raise ValidationError(_("Bonus rate cannot be negative."))
            if t.to_amount and t.to_amount <= t.from_amount:
                raise ValidationError(_(
                    "Tier 'To' (%s) must be greater than 'From' (%s), or 0 for "
                    "the top band.") % (_g(t.to_amount), _g(t.from_amount)))


class CollectionBonusPeriod(models.Model):
    _name = 'collection.bonus.period'
    _description = 'Collection Bonus Period'
    _order = 'date_from desc, id desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    company_id = fields.Many2one(
        'res.company', string='Branch / Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    config_id = fields.Many2one(
        'collection.bonus.config', string='Bonus Rule', required=True,
        default=lambda self: self._default_config())
    collector_user_id = fields.Many2one(
        related='config_id.collector_user_id', string='Collector',
        store=True, readonly=True)
    scope = fields.Selection(
        related='config_id.scope', string='Bonus Scope',
        store=True, readonly=True)
    calc_mode = fields.Selection(
        related='config_id.calc_mode', string='Calculation Mode', readonly=True)
    date_from = fields.Date(string='From', required=True,
                            default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='To', required=True,
                          default=fields.Date.context_today)
    collected_amount = fields.Monetary(string='Total Collected', readonly=True)
    bonus_amount = fields.Monetary(string='Bonus', readonly=True)
    payment_line_ids = fields.One2many(
        'collection.bonus.payment.line', 'period_id', string='Payments Counted')
    result_tier_ids = fields.One2many(
        'collection.bonus.result.tier', 'period_id', string='Bonus Breakdown')
    cashier_result_ids = fields.One2many(
        'collection.bonus.cashier.result', 'period_id', string='Per-Cashier Results')
    payment_count = fields.Integer(compute='_compute_payment_count')
    sms_batch_count = fields.Integer(compute='_compute_sms_batch_count')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('computed', 'Computed'),
         ('confirmed', 'Confirmed'),
         ('paid', 'Paid')],
        default='draft', copy=False)
    note = fields.Text()

    @api.model
    def _default_config(self):
        return self.env['collection.bonus.config'].search(
            [('company_id', 'in', (self.env.company.id, False)),
             ('active', '=', True)], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('collection.bonus.period')
                vals['name'] = seq or _('New')
        return super().create(vals_list)

    @api.depends('payment_line_ids')
    def _compute_payment_count(self):
        for p in self:
            p.payment_count = len(p.payment_line_ids)

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_sms_batch_count(self):
        Batch = self.env['collection.sms.batch']
        for p in self:
            if not p.date_from or not p.date_to:
                p.sms_batch_count = 0
                continue
            p.sms_batch_count = Batch.search_count([
                ('company_id', '=', p.company_id.id),
                ('date', '>=', p.date_from),
                ('date', '<=', p.date_to),
                ('state', 'in', ('generated', 'sent')),
            ])

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    def _collected_move_lines(self):
        """Receivable credit lines posted in bank/cash journals within the
        period that carry a customer = real money collected from customers.

        Requiring a partner drops POS session/closing settlements and other
        aggregate clearing entries (which post to a generic receivable with no
        customer). Sales-journal credit notes are already excluded by the
        bank/cash journal filter. Journals listed on the rule are also skipped.
        """
        self.ensure_one()
        domain = [
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('credit', '>', 0),
            ('journal_id.type', 'in', ('bank', 'cash')),
            ('partner_id', '!=', False),
        ]
        excluded = self.config_id.excluded_journal_ids
        if excluded:
            domain.append(('journal_id', 'not in', excluded.ids))
        # Single-collector scope: if the collector's journals are set, base the
        # bonus only on collections in those journals (this collector's own).
        if self.config_id.scope == 'single' and self.config_id.collector_journal_ids:
            domain.append(
                ('journal_id', 'in', self.config_id.collector_journal_ids.ids))
        return self.env['account.move.line'].search(domain)

    def _apply_tiers(self, total):
        """Return (bonus_total, [breakdown dicts]) for the collected total
        using the rule's shared tier table."""
        return _compute_tier_bonus(
            self.config_id.tier_ids, total, self.config_id.calc_mode)

    def action_compute(self):
        self.ensure_one()
        cfg = self.config_id
        if not cfg:
            raise UserError(_("Select a Bonus Rule first."))
        if self.date_to < self.date_from:
            raise UserError(_("'To' date must be on or after 'From' date."))
        per_cashier = cfg.scope == 'cashier'
        if not per_cashier and not cfg.tier_ids:
            raise UserError(_("The selected Bonus Rule has no tiers defined."))
        if per_cashier and not cfg.tier_ids and not any(
                c.tier_ids for c in cfg.cashier_ids):
            raise UserError(_(
                "Per-cashier scope needs either a shared tier table or "
                "per-cashier tiers defined on the rule."))
        if per_cashier and cfg.cashier_attribution == 'journal' and not any(
                c.journal_ids for c in cfg.cashier_ids):
            raise UserError(_(
                "Journal attribution needs each cashier's journals set on the "
                "rule. Add cashiers and assign their journals first."))

        self.payment_line_ids.unlink()
        self.result_tier_ids.unlink()
        self.cashier_result_ids.unlink()

        mls = self._collected_move_lines()
        total = sum(mls.mapped('credit'))
        self.payment_line_ids = [(0, 0, {
            'partner_id': ml.partner_id.id,
            'payment_date': ml.date,
            'amount': ml.credit,
            'move_id': ml.move_id.id,
            'journal_id': ml.journal_id.id,
            'user_id': ml.move_id.create_uid.id,
            'ref': ml.move_id.name or ml.move_id.ref or '',
        }) for ml in mls]
        self.collected_amount = total

        if not per_cashier:
            bonus, rows = self._apply_tiers(total)
            self.result_tier_ids = [(0, 0, r) for r in rows]
            self.bonus_amount = bonus
            msg = _('Collected %(c)s from %(n)d payment(s). Bonus: %(b)s.') % {
                'c': _g(total), 'n': len(mls), 'b': _g(bonus)}
        else:
            cashier_rows = list(cfg.cashier_ids)
            by_user_row = {c.user_id.id: c for c in cashier_rows}
            total_bonus = 0.0
            cashier_cmds = []

            if cfg.cashier_attribution == 'journal':
                # Each journal belongs to the cashier that owns it; a cashier
                # can own several journals. Payments in an unmapped journal go
                # to an "unassigned" bucket (shown, but earns no bonus).
                journal_to_row = {}
                for c in cashier_rows:
                    for j in c.journal_ids:
                        journal_to_row.setdefault(j.id, c)
                buckets = {}
                for ml in mls:
                    crow = journal_to_row.get(ml.journal_id.id)
                    key = crow.id if crow else None
                    b = buckets.setdefault(
                        key, {'row': crow, 'amount': 0.0, 'count': 0})
                    b['amount'] += ml.credit
                    b['count'] += 1
                ordered = sorted(
                    buckets.items(),
                    key=lambda kv: (kv[0] is None, -kv[1]['amount']))
                for key, b in ordered:
                    crow = b['row']
                    if crow:
                        tiers = crow.tier_ids if crow.tier_ids else cfg.tier_ids
                        bonus_u, rows_u = _compute_tier_bonus(
                            tiers, b['amount'], cfg.calc_mode)
                        total_bonus += bonus_u
                        cashier_cmds.append((0, 0, {
                            'user_id': crow.user_id.id,
                            'collected_amount': b['amount'],
                            'bonus_amount': bonus_u,
                            'payment_count': b['count'],
                            'uses_own_tiers': bool(crow.tier_ids),
                            'result_tier_ids': [(0, 0, r) for r in rows_u],
                        }))
                    else:
                        cashier_cmds.append((0, 0, {
                            'user_id': False,
                            'collected_amount': b['amount'],
                            'bonus_amount': 0.0,
                            'payment_count': b['count'],
                            'unassigned': True,
                        }))
                ncash = sum(1 for k in buckets if k is not None)
            else:
                # Attribute by the Odoo user who recorded each entry.
                by_user = {}
                for ml in mls:
                    user = ml.move_id.create_uid
                    rec = by_user.setdefault(
                        user.id, {'user': user, 'amount': 0.0, 'count': 0})
                    rec['amount'] += ml.credit
                    rec['count'] += 1
                for uid, rec in sorted(
                        by_user.items(), key=lambda kv: kv[1]['amount'], reverse=True):
                    crow = by_user_row.get(uid)
                    tiers = crow.tier_ids if (crow and crow.tier_ids) else cfg.tier_ids
                    bonus_u, rows_u = _compute_tier_bonus(
                        tiers, rec['amount'], cfg.calc_mode)
                    total_bonus += bonus_u
                    cashier_cmds.append((0, 0, {
                        'user_id': uid,
                        'collected_amount': rec['amount'],
                        'bonus_amount': bonus_u,
                        'payment_count': rec['count'],
                        'uses_own_tiers': bool(crow and crow.tier_ids),
                        'result_tier_ids': [(0, 0, r) for r in rows_u],
                    }))
                ncash = len(by_user)

            self.cashier_result_ids = cashier_cmds
            self.bonus_amount = total_bonus
            msg = _('Collected %(c)s from %(n)d payment(s) across %(k)d '
                    'cashier(s). Total bonus: %(b)s.') % {
                'c': _g(total), 'n': len(mls),
                'k': ncash, 'b': _g(total_bonus)}

        self.state = 'computed'
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _('Bonus computed'),
                'message': msg,
                'type': 'success', 'sticky': False,
            },
        }

    def action_confirm(self):
        for p in self:
            if p.state != 'computed':
                raise UserError(_("Compute the bonus before confirming."))
            p.state = 'confirmed'

    def action_mark_paid(self):
        for p in self:
            if p.state != 'confirmed':
                raise UserError(_("Confirm the bonus before marking it paid."))
            p.state = 'paid'

    def action_reset(self):
        for p in self:
            p.state = 'draft'

    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payments Counted'),
            'res_model': 'collection.bonus.payment.line',
            'view_mode': 'list',
            'domain': [('period_id', '=', self.id)],
        }

    def action_view_batches(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('SMS Batches'),
            'res_model': 'collection.sms.batch',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.company_id.id),
                       ('date', '>=', self.date_from),
                       ('date', '<=', self.date_to),
                       ('state', 'in', ('generated', 'sent'))],
        }


class CollectionBonusPaymentLine(models.Model):
    _name = 'collection.bonus.payment.line'
    _description = 'Collection Bonus Payment Line'
    _order = 'payment_date, id'

    period_id = fields.Many2one(
        'collection.bonus.period', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='period_id.currency_id', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer')
    payment_date = fields.Date(string='Date')
    amount = fields.Monetary(string='Amount Collected')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    journal_id = fields.Many2one('account.journal', string='Journal')
    user_id = fields.Many2one('res.users', string='Cashier (recorded by)')
    ref = fields.Char(string='Reference')

    def action_open_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }


class CollectionBonusResultTier(models.Model):
    _name = 'collection.bonus.result.tier'
    _description = 'Collection Bonus Result Tier'
    _order = 'from_amount, id'

    period_id = fields.Many2one(
        'collection.bonus.period', ondelete='cascade')
    cashier_result_id = fields.Many2one(
        'collection.bonus.cashier.result', ondelete='cascade')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id')
    name = fields.Char(string='Band')
    from_amount = fields.Monetary(string='From')
    to_amount = fields.Monetary(string='To')
    percent = fields.Float(string='Rate (%)')
    base_amount = fields.Monetary(string='Amount in Band')
    bonus_amount = fields.Monetary(string='Bonus')

    @api.depends('period_id.currency_id',
                 'cashier_result_id.period_id.currency_id')
    def _compute_currency_id(self):
        for r in self:
            period = r.period_id or r.cashier_result_id.period_id
            r.currency_id = period.currency_id if period \
                else self.env.company.currency_id


class CollectionBonusCashier(models.Model):
    _name = 'collection.bonus.cashier'
    _description = 'Collection Bonus Cashier'
    _order = 'user_id'

    config_id = fields.Many2one(
        'collection.bonus.config', required=True, ondelete='cascade')
    currency_id = fields.Many2one(
        related='config_id.currency_id', readonly=True)
    user_id = fields.Many2one(
        'res.users', string='Cashier', required=True,
        help="The Odoo user whose recorded collections this tier table applies to.")
    journal_ids = fields.Many2many(
        'account.journal', string='Journals',
        help="Journals (tills / mobile-money accounts) that belong to this "
             "cashier. Used when the rule attributes payments by journal. A "
             "cashier can own several journals.")
    tier_ids = fields.One2many(
        'collection.bonus.tier', 'cashier_id', string='Tiers',
        help="This cashier's own tier table. Leave empty to use the rule's "
             "shared tiers.")

    _sql_constraints = [
        ('uniq_cashier_per_config', 'unique(config_id, user_id)',
         'Each cashier can appear only once per bonus rule.'),
    ]

    @api.depends('user_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.user_id.name or _('Cashier')


class CollectionBonusCashierResult(models.Model):
    _name = 'collection.bonus.cashier.result'
    _description = 'Collection Bonus Per-Cashier Result'
    _order = 'bonus_amount desc, id'

    period_id = fields.Many2one(
        'collection.bonus.period', required=True, ondelete='cascade')
    currency_id = fields.Many2one(
        related='period_id.currency_id', readonly=True)
    user_id = fields.Many2one('res.users', string='Cashier')
    collected_amount = fields.Monetary(string='Collected')
    bonus_amount = fields.Monetary(string='Bonus')
    payment_count = fields.Integer(string='Payments')
    uses_own_tiers = fields.Boolean(
        string='Own Tiers',
        help="Ticked if this cashier's own tier table was used; otherwise the "
             "rule's shared tiers were applied.")
    unassigned = fields.Boolean(
        string='Unassigned',
        help="Collections in journals not mapped to any cashier. Shown for "
             "reconciliation; they earn no bonus until you assign the journal "
             "to a cashier and recompute.")
    result_tier_ids = fields.One2many(
        'collection.bonus.result.tier', 'cashier_result_id',
        string='Bonus Breakdown')

    def action_open_payments(self):
        self.ensure_one()
        cfg = self.period_id.config_id
        domain = [('period_id', '=', self.period_id.id)]
        if self.unassigned:
            owned = cfg.cashier_ids.mapped('journal_ids')
            domain.append(('journal_id', 'not in', owned.ids))
            name = _('Payments — Unassigned')
        elif cfg.cashier_attribution == 'journal':
            crow = cfg.cashier_ids.filtered(
                lambda c: c.user_id == self.user_id)[:1]
            domain.append(('journal_id', 'in', crow.journal_ids.ids))
            name = _('Payments — %s') % (self.user_id.name or '')
        else:
            domain.append(('user_id', '=', self.user_id.id))
            name = _('Payments — %s') % (self.user_id.name or '')
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'collection.bonus.payment.line',
            'view_mode': 'list',
            'domain': domain,
        }
