# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_restrict_negative = fields.Boolean(
        related="pos_config_id.is_restrict_negative",
        string="Restrict Negative stock",
        readonly=False)
