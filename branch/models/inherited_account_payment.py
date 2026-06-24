# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def default_get(self, default_fields):
        res = super(AccountPayment, self).default_get(default_fields)
        if self.env.user.branch_id and 'branch_id' in default_fields:
            res.update({
                'branch_id': self.env.user.branch_id.id or False
            })
        return res

    branch_id = fields.Many2one('res.branch')

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.state != 'draft':
            raise UserError(
                "You can only change the branch when the payment is in draft state.")
        selected_branch = self.branch_id
        user = self.env.user
        if selected_branch:
            if user.has_group('branch.group_multi_branch'):
                allowed_branch_ids = self.env.context.get(
                    'allowed_branch_ids', [])
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

    def action_post(self):
        for payment in self:
            if payment.reconciled_invoice_ids:
                for invoice in payment.reconciled_invoice_ids:
                    if invoice.branch_id != payment.branch_id:
                        raise UserError(
                            f"The payment's branch ({payment.branch_id.name}) must match the invoice's branch ({invoice.branch_id.name})."
                        )
        return super().action_post()
