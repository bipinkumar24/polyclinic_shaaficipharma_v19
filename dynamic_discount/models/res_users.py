# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    discount = fields.Boolean(
        string="Restrict Discount",
        help="If enabled, this cashier will not be allowed to apply the Global Discount in the POS session.",
    )
    discount_add = fields.Selection(
        string="Discount Type Restriction",
        selection=[("percentage", "Percentage"), ("amount", "Amount"), ("both", "Both")],
        help="Restrict the type of discount this cashier is allowed to apply.",
    )
    discount_amount_pos = fields.Float(
        string="Max Discount Amount",
        help="The maximum discount amount/percentage this cashier is allowed to apply in the POS session.",
    )
    is_user_pos_discount = fields.Boolean(
        string="Discount Restricted",
        compute='_compute_is_user_pos_discount',
        help="Technical field used in the POS frontend to hide the Global Discount button for this cashier.",
    )

    @api.depends('discount')
    def _compute_is_user_pos_discount(self):
        for user in self:
            user.is_user_pos_discount = user.discount

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        result += ['discount', 'discount_amount_pos', 'discount_add', 'is_user_pos_discount']
        return result
