# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PhysicianCommissionConfig(models.TransientModel):
    """Persistent global default for the allocated expense rate.

    Stored in a system parameter so it is set once and reused on every
    report run (still overridable per run and per physician)."""
    _name = 'physician.commission.config'
    _description = 'Physician Commission Settings'

    _PARAM = 'shafic_physician_commission.expense_rate'

    expense_rate = fields.Float(
        string='Default Expense Rate %', default=45.0,
        help='Default share of revenue deducted as allocated expense '
             'before the physician commission. Applies unless overridden '
             'per physician or changed on a report run.')
    journal_id = fields.Many2one(
        'account.journal', string='Commission Journal',
        domain="[('type', '=', 'general')]",
        help='Journal used for the commission journal entries.')
    expense_account_id = fields.Many2one(
        'account.account', string='Commission Expense Account',
        help='Debited with the commission amount.')
    payable_account_id = fields.Many2one(
        'account.account', string='Commission Payable Account',
        help='Credited with the commission amount (settled when you pay '
             'the physician).')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        icp = self.env['ir.config_parameter'].sudo()
        res['expense_rate'] = float(icp.get_param(self._PARAM, 45.0) or 0.0)
        company = self.env.company
        res['journal_id'] = \
            company.physician_commission_journal_id.id or False
        res['expense_account_id'] = \
            company.physician_commission_expense_account_id.id or False
        res['payable_account_id'] = \
            company.physician_commission_payable_account_id.id or False
        return res

    def action_save(self):
        self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param(
            self._PARAM, self.expense_rate)
        self.env.company.sudo().write({
            'physician_commission_journal_id': self.journal_id.id,
            'physician_commission_expense_account_id':
                self.expense_account_id.id,
            'physician_commission_payable_account_id':
                self.payable_account_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}
