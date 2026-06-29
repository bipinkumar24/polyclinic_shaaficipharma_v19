# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.tools.safe_eval import safe_eval


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sh_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
    )

    @api.onchange('product_id')
    def onchange_custom_product_id(self):
        self.sh_warehouse_id = self.order_id.picking_type_id.default_location_dest_id.warehouse_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('order_id'):
                order = self.env['purchase.order'].browse(vals['order_id'])
                if order.picking_type_id.warehouse_id:
                    vals['sh_warehouse_id'] = order.picking_type_id.warehouse_id.id
        return super(PurchaseOrderLine, self).create(vals_list)

    def _prepare_stock_moves(self, picking):
        # Huynv custom here
        if not self.sh_warehouse_id:
            self.sh_warehouse_id = self.order_id.picking_type_id.default_location_dest_id.warehouse_id or self.order_id.picking_type_id.default_location_src_id.warehouse_id
        # End custom

        data = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        if data:
            for value in data:
                value.update({
                    'picking_type_id': self.sh_warehouse_id.in_type_id.id,
                    'company_id': self.sh_warehouse_id.company_id.id,
                    'warehouse_id': self.sh_warehouse_id.id,
                    'route_ids': self.sh_warehouse_id and [
                        (6, 0, [x.id for x in self.sh_warehouse_id.route_ids])] or [],
                    'location_dest_id': self.sh_warehouse_id.in_type_id.default_location_dest_id.id
                })
        return data

    def _create_or_update_picking(self):
        for line in self:
            if line.product_id and line.product_id.type == 'consu':
                # Prevent decreasing below received quantity
                if float_compare(line.product_qty, line.qty_received, line.product_uom.rounding) < 0:
                    raise UserError(_('You cannot decrease the ordered quantity below the received quantity.\n'
                                      'Create a return first.'))

                if float_compare(line.product_qty, line.qty_invoiced, line.product_uom.rounding) == -1:
                    # If the quantity is now below the invoiced quantity, create an activity on the vendor bill
                    # inviting the user to create a refund.
                    line.invoice_lines[0].move_id.activity_schedule(
                        'mail.mail_activity_data_warning',
                        note=_(
                            'The quantities on your purchase order indicate less than billed. You should ask for a refund.'))

                # If the user increased quantity of existing line or created a new line
                pickings = line.order_id.picking_ids.filtered(
                    lambda x: x.state not in ('done', 'cancel') and x.location_dest_id.usage in (
                        'internal', 'transit', 'customer') and x.picking_type_id.id == line.order_id.picking_type_id.id)
                picking = pickings and pickings[0] or False
                if not picking:
                    res = line.order_id.with_context(
                        sh_warehouse_id=line.picking_type_id.warehouse_id.id)._prepare_picking()
                    picking = self.env['stock.picking'].create(res)
                moves = line._create_stock_moves(picking)
                moves._action_confirm()._action_assign()
