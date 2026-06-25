# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = "account.account"

    is_discount = fields.Boolean('Is Discount')