# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    card_commission_id = fields.Many2one(
        'res.card.commission',
        string='Card #',
        domain="[('state', '=', 'confirmed')]",
        copy=False,
    )
    commission_record_id = fields.Many2one(
        'pos.card.commission',
        string='Commission Record',
        copy=False,
    )

    def _create_invoice_card_commission(self):
        Commission = self.env['pos.card.commission'].sudo()
        for rec in self:
            if rec.move_type not in ('out_invoice', 'out_refund'):
                continue
            if not rec.card_commission_id or rec.commission_record_id:
                continue

            order_total = abs(rec.amount_total_signed or rec.amount_total)
            commission = rec.card_commission_id.percentage
            commission_record = Commission.create({
                'invoice_id': rec.id,
                'card_commission_id': rec.card_commission_id.id,
                'order_total': order_total,
                'commission': commission,
                'commission_amount': (order_total * commission) / 100 if order_total and commission else 0.0,
                'currency_id': rec.currency_id.id,
            })
            rec.commission_record_id = commission_record.id

    def action_post(self):
        res = super().action_post()
        self._create_invoice_card_commission()
        return res

    def action_view_commission_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Commission Record',
            'res_model': 'pos.card.commission',
            'res_id': self.commission_record_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
