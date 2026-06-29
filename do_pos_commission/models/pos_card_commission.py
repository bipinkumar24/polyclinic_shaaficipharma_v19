# -*- coding: utf-8 -*-

from odoo import fields, models, _,  api
from odoo.exceptions import UserError


class PosCardCommission(models.Model):
    _name = 'pos.card.commission'
    _rec_name = 'pos_order_id'
    _description = "Commission"
    _order = "id desc"

    pos_order_id = fields.Many2one('pos.order', string="Pos Order Ref")
    customer_name = fields.Many2one(related='pos_order_id.partner_id', string="Customer Name")
    card_commission_id = fields.Many2one('res.card.commission', string="Card Commission")
    order_total = fields.Monetary(string="Order Total")
    commission = fields.Float(string="Commission %")
    commission_amount = fields.Monetary(string='Commission Amount')
    journal_entry_id = fields.Many2one('account.move')
    # payment_id = fields.Many2one('account.payment')
    currency_id = fields.Many2one('res.currency', string='Currency')
    # status = fields.Selection([('unpaid', 'Unpaid'), ('paid', 'Paid')], default='unpaid', string='State')
    card_number = fields.Char(related="card_commission_id.card_number")
    partner_id = fields.Many2one(related="card_commission_id.partner_id", string="Partner")

    @api.onchange('order_total', 'commission')
    def _commission_amount(self):
        if self.order_total and self.commission:
            self.commission_amount = (self.order_total * self.commission) / 100

    @api.model
    def _order_fields(self, ui_order):
        data = super(PosCardCommission, self)._order_fields(ui_order)
        data.update({'card_commission_id': ui_order.get('card_commission_id', False)})
        return data

    # def action_create_journal_entry(self):
    #     view_id = self.env.ref('do_pos_commission.action_card_commission_payment').id
    #     return {
    #         'name': 'POS Card Commission Payment',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'commission.payment.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context':{
    #             'default_partner_id': self.partner_id.id,
    #             'default_amount' : self.commission_amount,
    #             'default_pos_card_commission_ids': self.ids,
    #         }
    #     }

    @api.model_create_multi
    def create(self, vals_list):
        orders = super(PosCardCommission, self).create(vals_list)
        # """Create Journal Entry for commission payment"""
        for rec in orders:
            if rec.journal_entry_id:
                continue
                # raise UserError(_("Journal Entry already exists for this commission."))
            company = rec.pos_order_id.company_id
            debit_acc = company.commission_debit_account_id
            credit_acc = company.commission_credit_account_id
            if not debit_acc or not credit_acc:
                raise UserError(_("Please configure Commission Debit and Credit accounts in Accounting Settings."))

            move = self.env['account.move'].create({
                'ref': f'Commission for POS Order {rec.pos_order_id.name}',
                'move_type': 'entry',
                'date': fields.Date.context_today(self),
                'line_ids': [
                    (0, 0, {
                        'account_id': debit_acc.id,
                        'partner_id': rec.partner_id.id if rec.partner_id else '',
                        'debit': rec.commission_amount,
                        'credit': 0.0,
                        'name': f'Commission {rec.card_commission_id.card_number}',
                    }),
                    (0, 0, {
                        'account_id': credit_acc.id,
                        'partner_id': rec.partner_id.id if rec.partner_id else '' ,
                        'debit': 0.0,
                        'credit': rec.commission_amount,
                        'name': f'Commission {rec.card_commission_id.card_number}',
                    }),
                ],
            })
            rec.journal_entry_id = move.id
            move.action_post()
        return orders

    # def action_register_commission_payment(self):
    #     unpaid = self.filtered(lambda r: r.status == 'unpaid')

    #     if not unpaid:
    #         raise UserError(_("All selected commissions are already paid."))

    #     if len(unpaid.mapped('partner_id')) > 1:
    #         raise UserError(_("You can only pay commissions for one partner at a time."))

    #     return {
    #         'name': _('Commission Payment'),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'commission.payment.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_pos_card_commission_ids': unpaid.ids,
    #             'default_partner_id': unpaid[0].partner_id.id,
    #             'default_amount': sum(unpaid.mapped('commission_amount')),
    #         }
    # }