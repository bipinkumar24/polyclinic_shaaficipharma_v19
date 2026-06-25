# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2024 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = "pos.config"

    # v15 field: singular Many2one — one stock location per POS config
    stock_location_id = fields.Many2one(
        "stock.location",
        string="Stock Location",
        domain=[("usage", "=", "internal")],
    )
