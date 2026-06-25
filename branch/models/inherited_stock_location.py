# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.model
    def default_get(self, default_fields):
        res = super(StockLocation, self).default_get(default_fields)
        branch_id = False
        if self.env.context.get('branch_id'):
            branch_id = self.env.context.get('branch_id')
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        if 'branch_id' in default_fields:
            res.update({'branch_id': branch_id})
        return res

    branch_id = fields.Many2one('res.branch')

    @api.constrains('branch_id')
    def _check_branch(self):
        warehouse_obj = self.env['stock.warehouse']
        warehouse_id = warehouse_obj.search(
            ['|', '|', ('wh_input_stock_loc_id', '=', self.id),
             ('lot_stock_id', '=', self.id),
             ('wh_output_stock_loc_id', '=', self.id)])
        for warehouse in warehouse_id:
            if self.branch_id != warehouse.branch_id:
                raise UserError(
                    _('Configuration error\nYou  must select same branch on a location as assigned on a warehouse configuration.'))

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
