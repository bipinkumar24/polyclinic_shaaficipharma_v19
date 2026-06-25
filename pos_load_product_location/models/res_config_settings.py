# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2024 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    stock_location_id = fields.Many2one(
        "stock.location",
        string="Stock Location",
        related="pos_config_id.stock_location_id",
        readonly=False,
    )
