# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api,_
from odoo.exceptions import UserError


class account_payment_register(models.TransientModel):
    _inherit = 'account.payment.register'

    loan_installment_id = fields.Many2one('loan.installment',string="Loan Installment",domain=[('state','=','approve')])

    @api.onchange('loan_installment_id')
    def onchange_loan_installment(self):
    	self.amount = self.loan_installment_id.emi_installment
    	self.partner_id = self.loan_installment_id.loan_id.user_id.partner_id.id
    	return

    def post(self):
        super(account_payment_register,self).post()
        for rec in self:
            if rec.loan_installment_id and rec.loan_installment_id.emi_installment == rec.amount : 
                rec.loan_installment_id.action_payment()
        return True
