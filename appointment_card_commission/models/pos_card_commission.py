# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosCardCommission(models.Model):
    _inherit = 'pos.card.commission'

    invoice_id = fields.Many2one(
        'account.move',
        string='Appointment Invoice',
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        invoice_vals = []
        pos_vals = []
        for vals in vals_list:
            if vals.get('invoice_id') and not vals.get('pos_order_id'):
                invoice_vals.append(vals)
            else:
                pos_vals.append(vals)

        records = self.browse()
        if pos_vals:
            records |= super().create(pos_vals)
        if invoice_vals:
            invoice_records = models.Model.create(self, invoice_vals)
            invoice_records._create_invoice_commission_journal_entry()
            records |= invoice_records
        return records

    def _create_invoice_commission_journal_entry(self):
        for rec in self.filtered(lambda record: record.invoice_id and not record.journal_entry_id):
            company = rec.invoice_id.company_id
            debit_acc = company.commission_debit_account_id
            credit_acc = company.commission_credit_account_id
            if not debit_acc or not credit_acc:
                raise UserError(_("Please configure Commission Debit and Credit accounts in Accounting Settings."))

            move = self.env['account.move'].create({
                'ref': _('Commission for Invoice %s') % (rec.invoice_id.name or rec.invoice_id.ref or rec.invoice_id.id),
                'move_type': 'entry',
                'date': rec.invoice_id.invoice_date or fields.Date.context_today(self),
                'company_id': company.id,
                'line_ids': [
                    (0, 0, {
                        'account_id': debit_acc.id,
                        'partner_id': rec.partner_id.id if rec.partner_id else False,
                        'debit': rec.commission_amount,
                        'credit': 0.0,
                        'name': _('Commission %s') % (rec.card_commission_id.card_number or ''),
                    }),
                    (0, 0, {
                        'account_id': credit_acc.id,
                        'partner_id': rec.partner_id.id if rec.partner_id else False,
                        'debit': 0.0,
                        'credit': rec.commission_amount,
                        'name': _('Commission %s') % (rec.card_commission_id.card_number or ''),
                    }),
                ],
            })
            rec.journal_entry_id = move.id
            move.action_post()
