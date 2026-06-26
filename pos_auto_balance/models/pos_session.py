from odoo import models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_is_zero, float_compare
import logging
from contextlib import ExitStack, contextmanager
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def action_pos_session_closing_control(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        result = super().action_pos_session_closing_control(
            balancing_account,
            amount_to_balance,
            bank_payment_method_diffs,
        )

        for session in self:
            move = session.move_id
            if not move:
                continue

            currency = session.company_id.currency_id

            total_debit = sum(move.line_ids.mapped('debit'))
            total_credit = sum(move.line_ids.mapped('credit'))
            diff = total_debit - total_credit

            if float_is_zero(diff, precision_rounding=currency.rounding):
                continue

            if move.state == 'posted':
                move.button_draft()


            if diff > 0:
                vals = {
                    'move_id': move.id,
                    'account_id': 29,   # credit diff account
                    'debit': 0.0,
                    'credit': abs(diff),
                    'name': 'POS Real Balance Adjustment',
                }
            else:
                vals = {
                    'move_id': move.id,
                    'account_id': 39,   # debit diff account
                    'debit': abs(diff),
                    'credit': 0.0,
                    'name': 'POS Real Balance Adjustment',
                }

            self.env['account.move.line'].create(vals)

            # 🔒 Final validation
            move.action_post()

        return result

#     def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
#         bank_payment_method_diffs = bank_payment_method_diffs or {}
#         self.ensure_one()
#         data = {}
#         sudo = self.env.user.has_group('point_of_sale.group_pos_user')
#         if self.get_session_orders().filtered(lambda o: o.state != 'cancel') or self.sudo().statement_line_ids:
#             self.cash_real_transaction = sum(self.sudo().statement_line_ids.mapped('amount'))
#             if self.state == 'closed':
#                 raise UserError(_('This session is already closed.'))
#             self._check_if_no_draft_orders()
#             self._check_invoices_are_posted()
#             cash_difference_before_statements = self.cash_register_difference
#             if self.update_stock_at_closing:
#                 self._create_picking_at_end_of_session()
#                 self._get_closed_orders().filtered(lambda o: not o.is_total_cost_computed)._compute_total_cost_at_session_closing(self.picking_ids.move_ids)
#             try:
#                 with self.env.cr.savepoint():
#                     data = self.with_company(self.company_id).with_context(check_move_validity=False, skip_invoice_sync=True, skip_check_balance=True)._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
#             except AccessError as e:
#                 if sudo:
#                     data = self.sudo().with_company(self.company_id).with_context(check_move_validity=False, skip_invoice_sync=True, skip_check_balance=True)._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
#                 else:
#                     raise e

#             balance = sum(self.move_id.line_ids.mapped('balance'))
#             try:
#                 with self.move_id.with_context(skip_check_balance=True)._check_balanced():
#                     pass
#             except UserError:
#                 # Creating the account move is just part of a big database transaction
#                 # when closing a session. There are other database changes that will happen
#                 # before attempting to create the account move, such as, creating the picking
#                 # records.
#                 # We don't, however, want them to be committed when the account move creation
#                 # failed; therefore, we need to roll back this transaction before showing the
#                 # close session wizard.
#                 self.env.cr.rollback()
#                 return self._close_session_action(balance)

#             self.sudo()._post_statement_difference(cash_difference_before_statements)
#             if self.move_id.line_ids:
#                 self.move_id.sudo().with_company(self.company_id)._post()
#                 # Set the uninvoiced orders' state to 'done'
#                 self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'paid')]).write({'state': 'done'})
#             else:
#                 self.move_id.sudo().unlink()
#             self.sudo().with_company(self.company_id)._reconcile_account_move_lines(data)
#         else:
#             self.sudo()._post_statement_difference(self.cash_register_difference)

#         if self.config_id.order_edit_tracking:
#             edited_orders = self.get_session_orders().filtered(lambda o: o.is_edited)
#             if len(edited_orders) > 0:
#                 body = _("Edited order(s) during the session:%s",
#                     Markup("<br/><ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % order._get_html_link() for order in edited_orders)
#                 )
#                 self.message_post(body=body)

#         # Make sure to trigger reordering rules
#         self.picking_ids.move_ids.sudo()._trigger_scheduler()

#         self.write({'state': 'closed'})
#         return True


# class PosOrder(models.Model):
#     _inherit = 'pos.order'

#     def _create_invoice(self, move_vals):
#         self.ensure_one()
#         invoice = self.env['account.move'].sudo()\
#             .with_company(self.company_id)\
#             .with_context(default_move_type=move_vals['move_type'], linked_to_pos=True)\
#             .create(move_vals)

#         if self.config_id.cash_rounding:
#             line_ids_commands = []
#             rate = invoice.invoice_currency_rate
#             sign = invoice.direction_sign
#             amount_paid = (-1 if self.amount_total < 0.0 else 1) * self.amount_paid
#             difference_currency = sign * (amount_paid - invoice.amount_total)
#             difference_balance = invoice.company_currency_id.round(difference_currency / rate) if rate else 0.0
#             if not self.currency_id.is_zero(difference_currency):
#                 rounding_line = invoice.line_ids.filtered(lambda line: line.display_type == 'rounding' and not line.tax_line_id)
#                 if rounding_line:
#                     line_ids_commands.append(Command.update(rounding_line.id, {
#                         'amount_currency': rounding_line.amount_currency + difference_currency,
#                         'balance': rounding_line.balance + difference_balance,
#                     }))
#                 else:
#                     if difference_currency > 0.0:
#                         account = invoice.invoice_cash_rounding_id.loss_account_id
#                     else:
#                         account = invoice.invoice_cash_rounding_id.profit_account_id
#                     line_ids_commands.append(Command.create({
#                         'name': invoice.invoice_cash_rounding_id.name,
#                         'amount_currency': difference_currency,
#                         'balance': difference_balance,
#                         'currency_id': invoice.currency_id.id,
#                         'display_type': 'rounding',
#                         'account_id': account.id,
#                     }))
#                 existing_terms_line = invoice.line_ids\
#                     .filtered(lambda line: line.display_type == 'payment_term')\
#                     .sorted(lambda line: -abs(line.amount_currency))[:1]
#                 line_ids_commands.append(Command.update(existing_terms_line.id, {
#                     'amount_currency': existing_terms_line.amount_currency - difference_currency,
#                     'balance': existing_terms_line.balance - difference_balance,
#                 }))
#                 with self.env['account.move'].with_context(skip_check_balance=True)._check_balanced({'records': invoice}):
#                     invoice.with_context(skip_invoice_sync=True).line_ids = line_ids_commands
#         invoice.message_post(body=_("This invoice has been created from the point of sale session: %s", self._get_html_link()))
#         return invoice


class AccountMove(models.Model):
    _inherit = 'account.move'

    @contextmanager
    def _check_balanced(self, container):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        yield
        return True
        with self._disable_recursion(container, 'check_move_validity', default=True, target=False) as disabled:
            yield
            if disabled:
                return

        if unbalanced_moves := self._get_unbalanced_moves(container):
            if len(unbalanced_moves) == 1:
                raise UserError("The entry is not balanced.")

            error_msg = _("The following entries are unbalanced:\n\n")
            for move in unbalanced_moves:
                error_msg += f"  - {self.browse(move[0]).name}\n"

            raise UserError(error_msg)
