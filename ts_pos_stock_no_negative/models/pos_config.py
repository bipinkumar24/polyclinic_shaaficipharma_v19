# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    is_restrict_negative = fields.Boolean(
        string="Restrict Negative Stock",
        help="When enabled, prevents selling products beyond the available quantity "
             "in the configured stock location(s).",
    )
