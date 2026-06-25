# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError


class PhysicianCommissionWizard(models.TransientModel):
    """Compute physician commission for a period.

    Rule: for each physician, deduct the allocated expense rate (default
    45%) from their clinic-service revenue, then pay their commission %
    on the remaining base.

    Revenue = posted customer invoices (ex-tax) for the physician's
    appointments, procedures and treatments. Credit notes net it down.
    """
    _name = 'physician.commission.wizard'
    _description = 'Physician Commission Report'

    date_from = fields.Date(
        string='From', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(
        string='To', required=True,
        default=fields.Date.context_today)
    expense_rate = fields.Float(
        string='Expense Rate %', required=True, default=45.0,
        help='Default share of revenue deducted as allocated expense '
             'before the physician commission. Pre-filled from the global '
             'setting; editable for this run. A physician with a custom '
             'expense rate uses theirs instead.')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        icp = self.env['ir.config_parameter'].sudo()
        res['expense_rate'] = float(icp.get_param(
            'shafic_physician_commission.expense_rate', 45.0) or 0.0)
        return res

    def _resolve_physician(self, move, treat_map):
        """Treating physician behind a clinic-service invoice."""
        if move.appointment_id and move.appointment_id.physician_id:
            return move.appointment_id.physician_id.id
        if move.procedure_id and move.procedure_id.physician_id:
            return move.procedure_id.physician_id.id
        return treat_map.get(move.id, False)

    def action_compute(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError("'From' date must be on or before 'To' date.")

        Line = self.env['physician.commission.line']
        Line.search([('wizard_id', '=', self.id)]).unlink()
        company = self.env.company

        # Reads run with elevated rights: this is a finance aggregate over
        # clinical records the finance user may not directly access.
        Move = self.env['account.move'].sudo()
        Treatment = self.env['hms.treatment'].sudo()
        Phys = self.env['hms.physician'].sudo()

        treatments = Treatment.search([
            ('invoice_id.state', '=', 'posted'),
            ('invoice_id.invoice_date', '>=', self.date_from),
            ('invoice_id.invoice_date', '<=', self.date_to),
        ])
        treat_map = {t.invoice_id.id: t.physician_id.id
                     for t in treatments if t.physician_id}
        treat_inv_ids = list(treat_map.keys())

        moves = Move.search([
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('company_id', '=', company.id),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            '|', '|',
            ('appointment_id', '!=', False),
            ('procedure_id', '!=', False),
            ('id', 'in', treat_inv_ids),
        ])

        revenue = defaultdict(float)
        for move in moves:
            phys_id = self._resolve_physician(move, treat_map)
            if not phys_id:
                continue
            sign = 1.0 if move.move_type == 'out_invoice' else -1.0
            revenue[phys_id] += sign * move.amount_untaxed

        rate_recs = self.env['physician.commission.rate'].sudo().search([])
        rate_map = {r.physician_id.id: r for r in rate_recs}
        default_exp = (self.expense_rate or 0.0) / 100.0

        for phys_id, rev in revenue.items():
            rate_rec = rate_map.get(phys_id)
            if rate_rec and rate_rec.override_expense:
                exp_rate = (rate_rec.expense_percent or 0.0) / 100.0
            else:
                exp_rate = default_exp
            expense = rev * exp_rate
            base = rev - expense
            pct = rate_rec.commission_percent if rate_rec else 0.0
            commission = base * pct / 100.0
            Line.create({
                'wizard_id': self.id,
                'physician_id': phys_id,
                'physician_name': Phys.browse(phys_id).name or '',
                'revenue': rev,
                'expense_rate_used': exp_rate * 100.0,
                'expense_amount': expense,
                'base_amount': base,
                'commission_percent': pct,
                'commission_amount': commission,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Physician Commission %s \u2192 %s' % (
                self.date_from, self.date_to),
            'res_model': 'physician.commission.line',
            'view_mode': 'list',
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
        }


class PhysicianCommissionLine(models.TransientModel):
    _name = 'physician.commission.line'
    _description = 'Physician Commission Line'
    _order = 'commission_amount desc'

    wizard_id = fields.Many2one('physician.commission.wizard',
                                ondelete='cascade', index=True)
    physician_id = fields.Many2one('hms.physician', readonly=True)
    physician_name = fields.Char(string='Physician', readonly=True)
    revenue = fields.Float(string='Revenue (ex-tax)', readonly=True)
    expense_rate_used = fields.Float(string='Expense %', readonly=True)
    expense_amount = fields.Float(string='Allocated Expense', readonly=True)
    base_amount = fields.Float(string='Base (after expense)', readonly=True)
    commission_percent = fields.Float(string='Rate %', readonly=True)
    commission_amount = fields.Float(string='Commission', readonly=True)

    def action_create_entries(self):
        """Create one draft journal entry per selected physician line:
        Dr commission expense / Cr commission payable, with the physician
        as partner on both lines. Left in draft for finance to review and
        post; skips lines already posted for the same period."""
        if not self:
            raise UserError(
                "Select at least one physician line (or use Select All), "
                "then click Create Journal Entries.")
        company = self.env.company
        journal = company.physician_commission_journal_id
        exp_acc = company.physician_commission_expense_account_id
        pay_acc = company.physician_commission_payable_account_id
        if not (journal and exp_acc and pay_acc):
            raise UserError(
                "Set the Commission Journal, Expense Account and Payable "
                "Account in Physician Commission \u2192 Settings first.")

        Move = self.env['account.move']
        created = Move.browse()
        skipped = []
        for line in self:
            if line.commission_amount <= 0:
                continue
            wiz = line.wizard_id
            df, dt = wiz.date_from, wiz.date_to
            phys = line.physician_id
            partner = phys.partner_id
            existing = Move.search([
                ('commission_physician_id', '=', phys.id),
                ('commission_date_from', '=', df),
                ('commission_date_to', '=', dt),
                ('state', '!=', 'cancel'),
            ], limit=1)
            if existing:
                skipped.append(line.physician_name)
                continue
            amount = line.commission_amount
            label = 'Physician commission %s: %s \u2192 %s' % (
                line.physician_name, df, dt)
            move = Move.create({
                'move_type': 'entry',
                'journal_id': journal.id,
                'date': dt,
                'ref': label,
                'commission_physician_id': phys.id,
                'commission_date_from': df,
                'commission_date_to': dt,
                'line_ids': [
                    (0, 0, {
                        'account_id': exp_acc.id,
                        'partner_id': partner.id or False,
                        'name': 'Commission %s' % line.physician_name,
                        'debit': amount, 'credit': 0.0,
                    }),
                    (0, 0, {
                        'account_id': pay_acc.id,
                        'partner_id': partner.id or False,
                        'name': 'Commission payable %s'
                                % line.physician_name,
                        'debit': 0.0, 'credit': amount,
                    }),
                ],
            })
            created |= move

        if not created:
            msg = "No journal entries created."
            if skipped:
                msg += " Already recorded for: %s." % ", ".join(skipped)
            raise UserError(msg)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Commission Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'target': 'current',
        }
