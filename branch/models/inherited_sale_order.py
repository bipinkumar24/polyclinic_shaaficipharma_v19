# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Domain


from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def default_get(self, fields):
        res = super(SaleOrder, self).default_get(fields)
        branch_id = warehouse_id = False
        if self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        if branch_id:
            branched_warehouse = self.env['stock.warehouse'].search([
                ('branch_id', '=', branch_id),
                ('company_id', '=', self.env.user.company_id.id)
            ], limit=1)

            if branched_warehouse:
                warehouse_id = branched_warehouse.id

        if 'branch_id' in fields:
            res.update({
                'branch_id': branch_id,
            })
        if 'warehouse_id' in fields and warehouse_id:
            res.update({
                'warehouse_id': warehouse_id,
            })

        return res

    branch_id = fields.Many2one('res.branch', string="Branch")

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res['branch_id'] = self.branch_id.id
        return res

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.state != 'draft':
            raise UserError(
                _("You can only change the branch when the Sale Order is in draft state."))

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
