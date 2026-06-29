# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CardCommissionPayment(models.TransientModel):
    _name = 'commission.payment.wizard'
    _description = 'Commission Payment Wizard'

    pos_card_commission_ids = fields.Many2many('pos.card.commission', string='POS Commissions')
    res_card_commission_id = fields.Many2one('res.card.commission')
    date = fields.Date('Payment Date', required=True)
    amount = fields.Monetary(string="Payment Amount")
    # payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', required=True)
    payment_name = fields.Char(string='Payment Reference')
    currency_id = fields.Many2one('res.currency', string='Currency')
    journal_id = fields.Many2one(comodel_name='account.journal', domain=[('type', 'in', ('cash', 'bank'))], store=True, readonly=False)
    partner_id = fields.Many2one('res.partner', string="Partner")

    # def commission_payment(self):
    #     for rec in self:
    #         if not rec.amount:
    #             raise UserError(_("Enter Payment Amount"))
    #         if rec.pos_card_commission_id and rec.res_card_commission_id:
    #             payment = self.env['account.payment'].create({
    #                 'payment_type': 'outbound',
    #                 'partner_id': rec.partner_id.id if rec.partner_id else '',
    #                 'amount': rec.amount,
    #                 'date': rec.date,
    #                 # 'pos_payment_method_id': rec.payment_method_id.id,
    #                 'payment_reference': rec.payment_name,
    #                 'journal_id': rec.journal_id.id,
    #                 'destination_account_id': self.env.user.company_id.commission_credit_account_id.id,
    #                 'is_commission_payment': True
    #                 })
    #             rec.pos_card_commission_id.payment_id = payment.id
    #             rec.pos_card_commission_id.status = 'paid'
    #             payment.action_post()

    @api.onchange('amount')
    def check_amount(self):
        if self.amount <= 0:
            raise ValidationError(_("The entered amount cannot be less than 0 the allowed balance."))
        elif self.amount > 0:
            if self.res_card_commission_id.balance < self.amount:
                raise ValidationError(_("The entered amount cannot be greater than the allowed balance."))
        


    def commission_payment(self):
        self.ensure_one()

        # commissions = self.pos_card_commission_ids.filtered(
        #     lambda r: r.status == 'unpaid'
        # )

        # if not commissions:
        #     raise UserError(_("No unpaid commissions found."))
        # partners = commissions.mapped('partner_id')
        # if len(partners) > 1:
        #     raise ValidationError(
        #         _("Selected commissions belong to different partners. "
        #           "Please select commissions for the same partner.")
        #     )


        # total = sum(commissions.mapped('commission_amount'))

        # if self.amount != self.res_card_commission_id.balance:
        #     raise ValidationError(
        #         _("Payment amount must equal total commission amount (%s).") % total
        #     )
        if self.amount:
            company = self.env.company
            credit_account = company.commission_credit_account_id
            if not credit_account:
                raise UserError(_("Configure Commission Credit Account in company settings."))

            payment = self.env['account.payment'].create({
                'payment_type': 'outbound',
                'res_card_commission_id': self.res_card_commission_id.id,
                'partner_id': self.partner_id.id,
                'amount': self.amount,
                'date': self.date,
                'journal_id': self.journal_id.id,
                'payment_reference': self.payment_name,
                'destination_account_id': credit_account.id,
                'is_commission_payment': True,
            })
            payment.action_post()
            # commissions.write({
            #     'payment_id': payment.id,
            #     'status': 'paid',
            # })