# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sales_price_per_pc = fields.Float(
        string="Sales Price Per Pc",
        digits='Product Price',
        help="Unit price used per piece when this product is settled from a "
             "prescription order in the Point of Sale.")
    uom_for_per_pc = fields.Many2one(
        'uom.uom',
        string="UOM for Per Pc",
        help="Unit of Measure used per piece when this product is settled from "
             "a prescription order in the Point of Sale.")
