# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    commission_debit_account_id = fields.Many2one(related="company_id.commission_debit_account_id", readonly=False)
    commission_credit_account_id = fields.Many2one(related="company_id.commission_credit_account_id", readonly=False)
