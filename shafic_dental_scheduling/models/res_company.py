# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    dental_block_double_booking = fields.Boolean(
        string='Block Dental Double-Booking', default=True,
        help='Prevent two dental appointments on the same dentist or the '
             'same chair at overlapping times.')
