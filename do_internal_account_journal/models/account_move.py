# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = "account.move"

    location_id = fields.Many2one("stock.location", "Location")

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for move in res:
            # Odoo 19 removed `stock.valuation.layer`; the journal entry is now
            # linked to its stock move(s) through `account.move.stock_move_ids`
            # (reverse of `stock.move.account_move_id`).
            if move.stock_move_ids:
                location_id = False
                stock_move = move.stock_move_ids[0]
                if stock_move.location_dest_id.usage == 'internal':
                    location_id = stock_move.location_dest_id
                if stock_move.location_id.usage == 'internal':
                    location_id = stock_move.location_id
                if location_id:
                    move.location_id = location_id.id
        res.update_location()
        return res

    def update_location(self):
        for move in self:
            stock_moves = move.stock_move_ids
            if stock_moves:
                picking_id = stock_moves[0].picking_id
                if picking_id.picking_type_code == "incoming":
                    move.location_id = picking_id.location_dest_id.id
                elif picking_id.picking_type_code == "outgoing":
                    move.location_id = picking_id.location_id.id
                elif picking_id.picking_type_code == "internal":
                    pass


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    location_id = fields.Many2one("stock.location", related="move_id.location_id", store=True, readonly=False)
    branch_id = fields.Many2one('res.branch', string="Branch", related="move_id.branch_id", store=True)
