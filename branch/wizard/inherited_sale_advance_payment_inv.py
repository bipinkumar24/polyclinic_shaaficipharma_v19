# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'


    def _create_invoice(self, order, so_line, amount):
        result = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)

        branch_id = False

        if order.branch_id:
            branch_id = order.branch_id.id
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        result.write({
            'branch_id' : branch_id
            })

        return result

class AccountPaymentRegisterInv(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields):
        rec = super(AccountPaymentRegisterInv, self).default_get(fields)
        invoice_defaults = self.env['account.move'].browse(self._context.get('active_id', []))
        if 'branch_id' in fields:
            if invoice_defaults and len(invoice_defaults) == 1:
                rec['branch_id'] = invoice_defaults.branch_id.id
        return rec

    branch_id = fields.Many2one('res.branch')

    def action_create_payments(self):
        for wizard in self:
            invoices = wizard.line_ids.mapped('move_id')
            for invoice in invoices:
                if invoice.branch_id != wizard.branch_id:
                    raise UserError(_(
                        "The selected branch '%s' does not match the branch '%s' of invoice '%s'. "
                        "Please select the correct branch before creating the payment."
                    ) % (wizard.branch_id.name, invoice.branch_id.name, invoice.name)
                )
        return super().action_create_payments()

    @api.onchange('branch_id')
    def _onchange_branch_id(self): 
        selected_branch = self.branch_id
        user = self.env.user 
        if selected_branch: 
            if user.has_group('branch.group_multi_branch'):
                allowed_branch_ids = self.env.context.get('allowed_branch_ids', [])
                if selected_branch.id not in allowed_branch_ids:
                    raise UserError(_(
                        "Please select an active branch only. Other branches may cause data inconsistency.\n\n"
                        "If you wish to work in another branch, switch to it using the top-right menu."
                    ))
            else: 
                if selected_branch != user.branch_id:
                    raise UserError(_(
                        "You are not allowed to switch branches.\n\n"
                        "Please use your assigned branch or contact an administrator."
                    ))
                    
    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result) 
        vals.update({'branch_id': self.branch_id.id})
        return vals