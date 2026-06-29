# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, SUPERUSER_ID, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Huynv: Comment do mỗi line sinh ra 1 picking => k hợp lý
    # def _create_picking(self):
    #     StockPicking = self.env['stock.picking']
    #     for order in self:
    #         order = order.with_company(order.company_id)
    #         for line in order.order_line.filtered(lambda l: l.product_id.type in ['product', 'consu']):
    #             pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel') and x.picking_type_id.id == line.sh_warehouse_id.in_type_id.id)
    #             if not pickings:
    #                 res = order.with_context(sh_warehouse_id=line.sh_warehouse_id.id)._prepare_picking()
    #                 picking = StockPicking.with_user(SUPERUSER_ID).create(res)
    #             else:
    #                 picking = pickings[0]
    #             moves = line._create_stock_moves(picking)
    #             moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
    #             seq = 0
    #             for move in sorted(moves, key=lambda move: move.date):
    #                 seq += 5
    #                 move.sequence = seq
    #             picking.message_post_with_source(
    #                 'mail.message_origin_link',
    #                 render_values={'self': picking, 'origin': order},
    #                 subtype_id=self.env.ref('mail.mt_note').id
    #             )
    #     return True

    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        ctx = self.env.context
        if ctx.get('sh_warehouse_id'):
            warehouse = self.env['stock.warehouse'].browse(ctx['sh_warehouse_id'])
            res.update({
                'picking_type_id': warehouse.in_type_id.id,
                'company_id': warehouse.company_id.id,
                'location_dest_id': warehouse.lot_stock_id.id,
            })
        return res

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id_for_line_sh_warehouse(self):
        for record in self:
            if record.picking_type_id:
                for line in record.order_line:
                    line.sh_warehouse_id = record.picking_type_id.warehouse_id