# -*- coding: utf-8 -*-

from odoo import fields, models, _, api
from odoo.exceptions import UserError


class PosOrderInherit(models.Model):
    _inherit = 'pos.order'

    card_commission_id = fields.Many2one('res.card.commission', string='Commission Card Number')
    card_commission_record_count = fields.Integer(string="Commission Record Count", compute="_card_commission_record_compute")

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.card_commission_id:
                debit_acc = []
                credit_acc = []
                if order.card_commission_id:
                    company = order.company_id

                    debit_acc = company.commission_debit_account_id
                    credit_acc = company.commission_credit_account_id
                if not debit_acc or not credit_acc:
                    raise UserError(_("Please configure Commission Debit and Credit accounts in Accounting Settings."))
                if order:
                    if order.card_commission_id and order.card_commission_id.percentage:
                        total = (order.amount_total * order.card_commission_id.percentage) / 100
                        self.env['pos.card.commission'].sudo().create({
                            'pos_order_id': order.id,
                            'customer_name': order.partner_id.id or False,
                            'card_commission_id': order.card_commission_id.id,  # must use .id here
                            'order_total': order.amount_total,
                            'commission': order.card_commission_id.percentage,
                            'commission_amount': total or 0.0,
                            'currency_id': order.pricelist_id.currency_id.id if order.pricelist_id else order.company_id.currency_id.id,
                        })
        return orders

    def _card_commission_record_compute(self):
        for rec in self:
            rec.card_commission_record_count = self.env['pos.card.commission'].search_count(
                [('pos_order_id', '=', rec.name)])

    def action_view_pos_card_commission(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commission Record'),
            'res_model': 'pos.card.commission',
            'domain': [('pos_order_id', '=', self.name)],
            'view_mode': 'list,kanban,form',
            'target': 'current'
        }
