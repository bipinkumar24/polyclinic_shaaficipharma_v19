# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_cashier_receipts = fields.Boolean('Is Cashier Receipts')
