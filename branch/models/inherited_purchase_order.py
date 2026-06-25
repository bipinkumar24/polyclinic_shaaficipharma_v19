# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError


class purchase_order(models.Model):

    _inherit = 'purchase.order.line'

    def _prepare_account_move_line(self, move=False):
        result = super(purchase_order, self)._prepare_account_move_line(move)
        result.update({
            'branch_id': self.order_id.branch_id.id or False,

        })
        return result

    @api.model
    def default_get(self, default_fields):
        res = super(purchase_order, self).default_get(default_fields)
        branch_id = False
        if self.env.context.get('branch_id'):
            branch_id = self.env.context.get('branch_id')
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        if 'branch_id' in default_fields:
            res.update({'branch_id': branch_id})
        return res

    branch_id = fields.Many2one('res.branch', string="Branch")

    def _prepare_stock_moves(self, picking):
        result = super(purchase_order, self)._prepare_stock_moves(picking)

        branch_id = False
        if self.branch_id:
            branch_id = self.branch_id.id
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        for res in result:
            res.update({'branch_id': branch_id})

        return result


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def default_get(self, fields):
        res = super(PurchaseOrder, self).default_get(fields)
        branch_id = picking_type_id = False

        if self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        if branch_id:
            branched_warehouse = self.env['stock.warehouse'].search(
                [('branch_id', '=', branch_id)])
            if branched_warehouse:
                picking_type_id = branched_warehouse[0].in_type_id.id

        if not picking_type_id:
            picking = self._default_picking_type()
            picking_type_id = picking.id

        if 'branch_id' in fields:
            res.update({
                'branch_id': branch_id,
                'picking_type_id': picking_type_id
            })

        return res
    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model_create_multi
    def create(self, vals_list):
        res = super(PurchaseOrder, self).create(vals_list)
        sale = self.env['sale.order'].sudo().search(
            [('name', '=', self.origin)], limit=1)
        if sale:
            res.update({
                'branch_id': sale.branch_id.id
            })
        return res

    @api.model
    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        branch_id = False
        if self.branch_id:
            branch_id = self.branch_id.id
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id
        res.update({
            'branch_id': branch_id
        })
        return res

    def _prepare_invoice(self):
        result = super(PurchaseOrder, self)._prepare_invoice()
        branch_id = False
        if self.branch_id:
            branch_id = self.branch_id.id
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        result.update({

            'branch_id': branch_id
        })

        return result

    def action_view_invoice(self, invoices=False):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''

        result = super(PurchaseOrder, self).action_view_invoice(invoices)

        branch_id = False
        if self.branch_id:
            branch_id = self.branch_id.id
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        result.update({
            'branch_id': branch_id
        })

        return result

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.state != 'draft':
            raise UserError(
                _("You can only change the branch when the Purchase Order is in draft state."))

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

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        for order in self.filtered(lambda po: po.state in ('purchase', 'done')):
            if any(product.type in ['product', 'consu'] for product in order.order_line.product_id):
                order = order.with_company(order.company_id)
                pickings = order.picking_ids.filtered(
                    lambda x: x.state not in ('done', 'cancel'))
                if not pickings:
                    res = order._prepare_picking()
                    picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                    pickings = picking
                else:
                    picking = pickings[0]
                moves = order.order_line._create_stock_moves(picking)
                moves = moves.filtered(lambda x: x.state not in (
                    'done', 'cancel'))._action_confirm()
                seq = 0
                for move in sorted(moves, key=lambda move: move.date):
                    seq += 5
                    move.sequence = seq
                moves._action_assign()
                # Get following pickings (created by push rules) to confirm them as well.
                forward_pickings = self.env['stock.picking']._get_impacted_pickings(
                    moves)
                if self.branch_id:
                    for record in forward_pickings:
                        record.branch_id = self.branch_id.id
                (pickings | forward_pickings).action_confirm()
                picking.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': picking, 'origin': order},
                    subtype_xmlid='mail.mt_note',
                )
        return True
