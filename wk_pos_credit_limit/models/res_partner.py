# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################
from odoo import fields, models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    credit_hold = fields.Boolean(string="Credit Hold", help="If this Field is Enabled then the Customer's Credit will be on Hold")
    block_credit_after_limit = fields.Boolean(string="Block Credit After Limit", help="If this Field gets Enabled then if the Customer's credit limit exceed's the given Credit Amount then the Customer will be blocked and will not be able to make any Orders")
    wk_credit_limit = fields.Integer(string="Credit Limit ", help="This Field shows the Credit Limit of a Customer")
    credit_hold_if_order_discount = fields.Boolean(string="Credit Hold if Order Discount", help="If this field is Enabled then the Customer's Credit will be on hold if any discount is applicable or applied")
    
    @api.model
    def _load_pos_data_fields(self, config):
        res = super()._load_pos_data_fields(config)
        res.extend(['credit_hold', 'block_credit_after_limit', 'wk_credit_limit', 'credit_hold_if_order_discount', 'credit'])
        return res

    @api.model
    def check_update_credit(self, partner_id, session_id, customer_account_id, customer_account_amount):
        session_credit = 0.0
        if partner_id:
            partner_orders = self.env['pos.order'].search([
                ('partner_id', '=', partner_id),
                ('session_id', '=', session_id),
            ])
            for order in partner_orders:
                for payment in order.payment_ids:
                    if (
                        payment.payment_method_id.id == customer_account_id
                        and not order.is_invoiced
                    ):
                        session_credit += payment.amount

        return session_credit + customer_account_amount
