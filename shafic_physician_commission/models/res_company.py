# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    physician_commission_journal_id = fields.Many2one(
        'account.journal', string='Commission Journal',
        domain="[('type', '=', 'general')]")
    physician_commission_expense_account_id = fields.Many2one(
        'account.account', string='Commission Expense Account')
    physician_commission_payable_account_id = fields.Many2one(
        'account.account', string='Commission Payable Account')
