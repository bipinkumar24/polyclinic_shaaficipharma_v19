from odoo import api, fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    closing_journal_id = fields.Many2one(
        'account.journal', string='Bank Journal',
        compute='_compute_closing_journal',
        help="Bank journal the POS register reconciles through. Computed "
             "on the fly \u2014 not stored.")
    cash_expected_amount = fields.Monetary(
        string='Expected', compute='_compute_cash_difference_gl',
        help="Total the system expected across the counted payment "
             "methods \u2014 the receivable cleared by each settlement "
             "entry posted when the session closed.")
    cash_actual_amount = fields.Monetary(
        string='Actual', compute='_compute_cash_difference_gl',
        help="Total the cashier actually recorded at closing across the "
             "counted payment methods. Equals Expected plus the closing "
             "difference.")
    cash_gain_amount = fields.Monetary(
        string='Cash Difference Gain', compute='_compute_cash_difference_gl',
        help="Overage \u2014 the counting differences booked to the Cash "
             "Difference Gain account, across the session entry and every "
             "payment-method settlement entry.")
    cash_loss_amount = fields.Monetary(
        string='Cash Difference Loss', compute='_compute_cash_difference_gl',
        help="Shortage \u2014 the counting differences booked to the Cash "
             "Difference Loss account, across the session entry and every "
             "payment-method settlement entry.")
    cash_difference_amount = fields.Monetary(
        string='Difference', compute='_compute_cash_difference_gl',
        help="Net closing difference: gain less loss. Positive is an "
             "overage, negative a shortage.")

    @api.depends('config_id', 'config_id.payment_method_ids')
    def _compute_closing_journal(self):
        for session in self:
            journals = session.config_id.payment_method_ids.mapped('journal_id')
            bank = journals.filtered(lambda j: j.type == 'bank')
            session.closing_journal_id = bank[:1] or journals[:1]

    def _diff_accounts(self):
        """The Cash Difference Gain / Loss accounts to read. Preference:
        the company-level setting; otherwise the profit / loss accounts of
        every payment journal on the register."""
        self.ensure_one()
        company = self.company_id or self.env.company
        accounts = (company.cash_diff_gain_account_id
                    | company.cash_diff_loss_account_id)
        if not accounts:
            for journal in self.config_id.payment_method_ids.mapped('journal_id'):
                accounts |= journal.profit_account_id | journal.loss_account_id
        return accounts

    @staticmethod
    def _ref_cites_session(ref, name):
        """True when `ref` mentions session `name` as a whole reference and
        not merely as the prefix of a longer number (POS/00412 inside
        POS/004120)."""
        if not ref or not name:
            return False
        start = 0
        while True:
            hit = ref.find(name, start)
            if hit == -1:
                return False
            tail = ref[hit + len(name): hit + len(name) + 1]
            if not tail.isdigit():
                return True
            start = hit + 1

    @api.depends('config_id')
    def _compute_cash_difference_gl(self):
        """Closing figures read from the posted journal entries.

        When a session closes, POS posts one settlement entry per counted
        payment method \u2014 'Combine <Method> ... POS payments from
        POS/#####'. Each balances the recorded receivable (Expected)
        against what the cashier counted (Actual); the over / short lands
        on the Cash Difference Gain / Loss accounts. Any cash rounding
        sits on the session's own move (move_id).

        This reads the session move and every settlement entry that cites
        the session, so the difference is the real counting over / short
        \u2014 not just rounding. Non-stored and defensive: any unexpected
        condition yields zero."""
        AM = self.env['account.move']
        for session in self:
            expected = difference = 0.0
            try:
                accounts = session._diff_accounts()
                main = (session.move_id
                        if 'move_id' in session._fields else False)
                # Cash rounding carried on the session's own entry.
                if accounts and main:
                    for line in main.line_ids:
                        if line.account_id in accounts:
                            difference += line.credit - line.debit
                # Per-payment-method settlement entries.
                name = session.name or ''
                if name:
                    moves = AM.search([('ref', 'ilike', name),
                                       ('state', '=', 'posted')])
                    for move in moves:
                        if main and move.id == main.id:
                            continue
                        if not session._ref_cites_session(move.ref or '',
                                                          name):
                            continue
                        for line in move.line_ids:
                            if line.account_id in accounts:
                                difference += line.credit - line.debit
                            else:
                                # Receivable cleared by the settlement
                                # entry = what the system expected.
                                expected += line.credit
            except Exception:
                expected = difference = 0.0
            session.cash_expected_amount = expected
            session.cash_actual_amount = expected + difference
            session.cash_difference_amount = difference
            session.cash_gain_amount = difference if difference > 0 else 0.0
            session.cash_loss_amount = -difference if difference < 0 else 0.0
