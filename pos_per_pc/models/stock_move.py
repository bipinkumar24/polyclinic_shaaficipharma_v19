# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _pos_perpc_order_lines(self, related_order_lines):
        """Return the related POS order lines that drive this move and are sold
        "per pc": a lot-tracked product whose line UOM is the product's
        configured `uom_for_per_pc` (carried over as `second_uom_id`)."""
        self.ensure_one()
        product = self.product_id
        if product.tracking == 'none' or not product.uom_for_per_pc:
            return self.env['pos.order.line']
        if self.product_uom != product.uom_for_per_pc:
            return self.env['pos.order.line']
        return related_order_lines.filtered(
            lambda l: l.product_id == product
            and l.second_uom_id == product.uom_for_per_pc
        )

    def _add_mls_related_to_order(self, related_order_lines, are_qties_done=True):
        """Handle per-pc lot-tracked moves with a silent FIFO lot pick, and let
        the standard (bi_pos_multi_uom) implementation deal with everything
        else."""
        perpc_moves = self.browse()
        for move in self:
            if move._pos_perpc_order_lines(related_order_lines):
                perpc_moves |= move

        for move in perpc_moves:
            move._pos_perpc_assign_lots(are_qties_done)

        remaining = self - perpc_moves
        if remaining:
            return super(
                StockMove, remaining
            )._add_mls_related_to_order(related_order_lines, are_qties_done)

    def _pos_perpc_assign_lots(self, are_qties_done):
        """Deduct the move quantity (in PC) from the on-hand stock of the
        lot-tracked product by allocating it across available lots FIFO."""
        self.ensure_one()
        self.move_line_ids.unlink()

        base_uom = self.product_id.uom_id
        rounding = base_uom.rounding
        # Move quantity is expressed in the per-pc UOM; convert to the base UOM
        # the lots/quants are stored in.
        base_qty = self.product_uom._compute_quantity(self.product_uom_qty, base_uom)
        if float_is_zero(base_qty, precision_rounding=rounding):
            return

        allocations = self._pos_perpc_fifo_allocation(base_qty)
        if not allocations:
            return

        if are_qties_done:
            move_line_vals = []
            for lot, qty in allocations:
                vals = dict(self._prepare_move_line_vals(qty))
                vals['lot_id'] = lot.id
                move_line_vals.append(vals)
            self.env['stock.move.line'].create(move_line_vals)
        else:
            for lot, qty in allocations:
                self._update_reserved_quantity(
                    qty, self.location_id, lot_id=lot, strict=False)

    def _pos_perpc_fifo_allocation(self, base_qty):
        """Allocate `base_qty` (in the product's base UOM) across available
        internal-location lots, oldest stock first. Returns a list of
        (lot, qty) tuples."""
        self.ensure_one()
        rounding = self.product_id.uom_id.rounding
        quants = self.env['stock.quant'].sudo().search(
            [
                ('product_id', '=', self.product_id.id),
                ('location_id', 'child_of', self.location_id.id),
                ('location_id.usage', '=', 'internal'),
                ('lot_id', '!=', False),
            ],
            order='in_date, id',
        )

        allocations = []
        remaining = base_qty
        for quant in quants:
            available = quant.quantity - quant.reserved_quantity
            if float_compare(available, 0.0, precision_rounding=rounding) <= 0:
                continue
            take = min(available, remaining)
            allocations.append((quant.lot_id, take))
            remaining -= take
            if float_compare(remaining, 0.0, precision_rounding=rounding) <= 0:
                break

        if float_compare(remaining, 0.0, precision_rounding=rounding) > 0:
            # Not enough on-hand across lots: pile the shortfall on the last
            # allocated lot (it will go negative), or fall back to the most
            # recent known lot if there is no stock at all.
            if allocations:
                lot, qty = allocations[-1]
                allocations[-1] = (lot, qty + remaining)
            else:
                lot = self.env['stock.lot'].sudo().search(
                    [('product_id', '=', self.product_id.id)],
                    order='create_date desc', limit=1)
                if lot:
                    allocations.append((lot, base_qty))

        return allocations
