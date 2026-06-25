# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    apply_discount = fields.Boolean(string='Apply Discount')
    discount_type = fields.Selection(
        [('fixed', 'Fixed'), ('percentage', 'Percentage')],
        string='Discount Type'
    )
    discount_amount = fields.Float(string='Discount Amount')
    percentage = fields.Float(string='Percentage (%)')

    @api.constrains('percentage')
    def _check_percentage(self):
        for rec in self:
            if rec.discount_type == 'percentage':
                if rec.percentage < 0 or rec.percentage > 100:
                    raise ValidationError(
                        _("Discount percentage must be between 0 and 100.")
                    )

    @api.constrains('discount_amount')
    def _check_discount_amount(self):
        for rec in self:
            if rec.discount_type == 'fixed' and rec.discount_amount < 0:
                raise ValidationError(
                    _("Discount amount cannot be negative.")
                )

    def _get_discount_amount(self):
        self.ensure_one()

        if not self.apply_discount:
            return 0.0

        if self.discount_type == 'percentage':
            return self.amount * (self.percentage / 100)

        return self.discount_amount

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        o0000000
        self.ensure_one()

        if write_off_line_vals is None:
            write_off_line_vals = []

        res = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance
        )

        if not self.apply_discount:
            return res

        discount = self._get_discount_amount()

        if discount <= 0:
            return res

        if discount >= self.amount:
            raise UserError(
                _("Discount cannot be greater than or equal to payment amount.")
            )

        discount_account = self.env['account.account'].search([
            ('is_discount', '=', True),
            ('company_ids', 'in', [self.company_id.id])
        ], limit=1)

        if not discount_account:
            raise UserError(
                _("Please configure a Discount Account with 'Is Discount = True'.")
            )

        discount_balance = self.currency_id._convert(
            discount,
            self.company_id.currency_id,
            self.company_id,
            self.date or fields.Date.today(),
        )

        target_line_found = False

        for line in res:
            # Inbound payment -> reduce debit liquidity line
            if self.payment_type == 'inbound':
                if line.get('debit', 0.0) > 0:
                    if line['debit'] < discount_balance:
                        raise UserError(
                            _("Discount exceeds payment amount.")
                        )

                    line['debit'] -= discount_balance
                    line['amount_currency'] = line.get('amount_currency', 0.0) - discount
                    target_line_found = True
                    break

            # Outbound payment -> reduce credit liquidity line
            elif self.payment_type == 'outbound':
                if line.get('credit', 0.0) > 0:
                    if line['credit'] < discount_balance:
                        raise UserError(
                            _("Discount exceeds payment amount.")
                        )

                    line['credit'] -= discount_balance
                    line['amount_currency'] = line.get('amount_currency', 0.0) + discount
                    target_line_found = True
                    break

        if not target_line_found:
            raise UserError(
                _("Could not find the payment move line to apply discount.")
            )

        # Create discount move line
        if self.payment_type == 'inbound':
            discount_line = {
                'name': _('Payment Discount'),
                'account_id': discount_account.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': discount,
                'debit': discount_balance,
                'credit': 0.0,
            }

        elif self.payment_type == 'outbound':
            discount_line = {
                'name': _('Payment Discount'),
                'account_id': discount_account.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -discount,
                'debit': 0.0,
                'credit': discount_balance,
            }

        else:
            return res

        res.append(discount_line)

        _logger.info("Discount line added: %s", discount_line)

        return res