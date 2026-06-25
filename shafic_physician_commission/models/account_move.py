# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    commission_physician_id = fields.Many2one(
        'hms.physician', string='Commission Physician', copy=False,
        index=True)
    commission_date_from = fields.Date(string='Commission From',
                                       copy=False)
    commission_date_to = fields.Date(string='Commission To', copy=False)
