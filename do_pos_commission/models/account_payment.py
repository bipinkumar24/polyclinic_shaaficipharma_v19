# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_commission_payment = fields.Boolean(string='Is Commission Payment', default=False)
    res_card_commission_id = fields.Many2one('res.card.commission', string='Card Commission')
