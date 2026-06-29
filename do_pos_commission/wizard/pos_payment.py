# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    def check(self):
        res = super(PosMakePayment, self).check()
        order = self.env['pos.order'].browse(self.env.context.get('active_id'))
        company = order.company_id
        debit_acc = company.commission_debit_account_id
        credit_acc = company.commission_credit_account_id
        if not debit_acc or not credit_acc:
                raise UserError(_("Please configure Commission Debit and Credit accounts in Accounting Settings."))
        if order:
            order_name = order.name  # use a separate variable if you need the name
            if order.clinic_id and order.clinic_id.percentage:
                total = (order.amount_total * order.clinic_id.percentage) / 100
                self.env['pos.commission'].sudo().create({
                    'pos_order_id': order.id,
                    'customer_name': order.partner_id.id,
                    'clinic_id': order.clinic_id.id,  # must use .id here
                    'order_total': order.amount_total,
                    'commission': order.clinic_id.percentage,
                    'commission_amount': total or 0.0,
                    'currency_id': order.pricelist_id.currency_id.id if order.pricelist_id else order.company_id.currency_id.id,
                })
        return res

