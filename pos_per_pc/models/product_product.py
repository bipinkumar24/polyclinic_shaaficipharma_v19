# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Exposed from the template so the values are reachable on the variant
    # (and loaded into the POS) just like the standard list_price / lst_price.
    sales_price_per_pc = fields.Float(
        related='product_tmpl_id.sales_price_per_pc',
        store=True, readonly=False,
        digits='Product Price',
        string="Sales Price Per Pc")
    uom_for_per_pc = fields.Many2one(
        related='product_tmpl_id.uom_for_per_pc',
        store=True, readonly=False,
        string="UOM for Per Pc")

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['sales_price_per_pc', 'uom_for_per_pc']
        return params
