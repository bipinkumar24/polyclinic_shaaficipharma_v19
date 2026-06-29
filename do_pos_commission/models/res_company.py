# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    commission_debit_account_id = fields.Many2one('account.account', string="Debit Account")
    commission_credit_account_id = fields.Many2one('account.account', string="Credit Account")
