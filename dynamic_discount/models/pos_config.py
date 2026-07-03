# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    global_discount_type = fields.Selection(related='pos_config_id.global_discount_type', readonly=False)
    global_discount_product_id = fields.Many2one('product.product', string="Discount Product", related='pos_config_id.global_discount_product_id', readonly=False)
    enable_discount = fields.Boolean(string="Enable Discount", related="pos_config_id.enable_discount", readonly=False)

class PosConfig(models.Model):
    _inherit = "pos.config"

    global_discount_type = fields.Selection(string="Global Discount Type", selection=[("percentage", "Percentage"), ("amount", "Amount"), ("both", "Both")], default="percentage")
    global_discount_product_id = fields.Many2one('product.product', string="Global Discount Product")
    enable_discount = fields.Boolean(string="Enable Discount")

    def _get_special_products(self):

        products = super()._get_special_products()
        discount_products = self.env['pos.config'].sudo().search(
            [('global_discount_product_id', '!=', False)]
        ).global_discount_product_id
        return products | discount_products
