# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2024 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = "pos.config"

    # Many2many — multiple stock locations can be selected per POS config
    stock_location_ids = fields.Many2many(
        "stock.location",
        "pos_config_stock_location_rel",
        "pos_config_id",
        "stock_location_id",
        string="Stock Locations",
        domain=[("usage", "=", "internal")],
    )
