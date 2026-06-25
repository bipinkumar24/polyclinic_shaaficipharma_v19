# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def default_get(self, default_fields):
        res = super(AccountMove, self).default_get(default_fields)
        branch_id = self.env.context.get('branch_id')
        if branch_id:
            if 'branch_id' in default_fields:
                res.update({'branch_id': branch_id})
        elif self.env.user.branch_id:
            if 'branch_id' in default_fields:
                res.update({'branch_id': self.env.user.branch_id.id})
        return res

    branch_id = fields.Many2one('res.branch', string="Branch")

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.state != 'draft':
            raise UserError(
                "You can only change the branch when the invoice is in draft state.")
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
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                sale_order = self.env['sale.order'].search(
                    [('invoice_ids', 'in', move.ids)], limit=1)
                if sale_order and move.branch_id.id != sale_order.branch_id.id:
                    raise UserError(_(
                        f"The Invoice's branch ({move.branch_id.name}) must match the sale order's branch ({sale_order.branch_id.name})."
                    ))

            elif move.move_type in ('in_invoice', 'in_refund'):
                purchase_order = self.env['purchase.order'].search(
                    [('invoice_ids', 'in', move.ids)], limit=1)
                if purchase_order and move.branch_id.id != purchase_order.branch_id.id:
                    raise UserError(_(
                        f"The Invoice's branch ({move.branch_id.name}) must match the purchase order's branch ({purchase_order.branch_id.name})."
                    ))

        return super().action_post()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def default_get(self, default_fields):
        res = super(AccountMoveLine, self).default_get(default_fields)
        branch_id = self.env.context.get('branch_id')
        if branch_id:
            if 'branch_id' in default_fields:
                res.update({'branch_id': branch_id})
        elif self.env.user.branch_id:
            if 'branch_id' in default_fields:
                res.update({'branch_id': self.env.user.branch_id.id})

        if self.move_id.branch_id:
            if 'branch_id' in default_fields:
                res.update({'branch_id': self.move_id.branch_id.id})
        return res

    branch_id = fields.Many2one(
        'res.branch', string="Branch", related="move_id.branch_id", store=True)
