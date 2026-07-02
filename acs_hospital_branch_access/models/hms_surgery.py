#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class AcsPatientSurgery(models.Model):
    _inherit = "hms.surgery"

    based_on = fields.Selection([('cash', 'Cash'), ('credit', 'Credit')], string='Customer Type')
    surgery_payment_id = fields.Many2one('account.payment', string="Laboratory Payment", copy=False)

    @api.model_create_multi
    def default_get(self, default_fields):
        res = super(AcsPatientSurgery, self).default_get(default_fields)
        if 'branch_id' in default_fields:
            if self.env.user.branch_id:
                res.update({
                    'branch_id': self.env.user.branch_id.id or False
                })
        return res

    branch_id = fields.Many2one('res.branch', string="Branch")

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
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

    def view_payment(self):
        self.ensure_one()
        if not self.surgery_payment_id:
            return False

        return {
            'name': 'Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.surgery_payment_id.id,
            'target': 'current',
        }

    def button_accept(self):
        company_id = self.sudo().company_id
        if not self.invoice_id:
            raise UserError(_('Invoice has not been created yet. Please create it first.'))
        else:
            self.state = 'accepted'


class AccountMove(models.Model):
    _inherit = "account.move"

    surgery_request_move_ids = fields.Many2many(
        "hms.surgery",
        "account_move_surgery_request_rel",  # relation table
        "move_id",
        "surgery_request_id",
        string="Surgery Requests"
    )

    def action_post(self):
        res = super().action_post()
        for move in self:
            surgery_request_move_ids = move.surgery_request_move_ids
            if surgery_request_move_ids:
                surgery_request_move_ids.button_accept()
        return res
