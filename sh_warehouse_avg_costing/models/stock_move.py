# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
#
# Odoo 19 migration note
# ----------------------
# In Odoo 19 the model ``stock.valuation.layer`` (SVL) has been removed. Inventory
# valuation is now stored directly on ``stock.move.value`` and the global average
# cost is maintained by Odoo through ``stock.move._set_value`` /
# ``product.product._update_standard_price``.
#
# This module keeps maintaining its OWN warehouse-wise average cost in the
# ``sh.warehouse.cost`` model (Odoo's native warehouse valuation only apportions the
# single global average by quantity, it does NOT keep a distinct average per
# warehouse). To preserve the original behaviour we now hook into the new
# valuation entry points:
#   * incoming valued moves  -> blend the destination warehouse average cost
#   * internal transfers between two warehouses -> shift cost between buckets
#   * outgoing valued moves  -> value at the *source* warehouse cost (this makes
#                               both the inventory valuation and the COGS
#                               warehouse-specific, exactly like the old override
#                               of ``_prepare_out_svl_vals`` /
#                               ``_stock_account_get_anglo_saxon_price_unit`` did).
#
# IMPORTANT: the numeric results of warehouse-wise costing must be validated on a
# real database. The accounting flow itself is now handled by Odoo core.

from odoo import fields, models


class WarehouseStockMove(models.Model):
    _inherit = "stock.move"

    sh_in_replenshment = fields.Boolean("Is Replenishment")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def get_quantity_from_valuation(self, productid, warehouseid):
        """Return the on-hand quantity of ``productid`` inside ``warehouseid``.

        Odoo 19 removed ``stock.valuation.layer`` so the per-warehouse quantity is
        now read through the native warehouse-aware ``qty_available`` (which also
        honours the ``to_date`` context for the historical reports).
        """
        if not productid or not warehouseid:
            return 0.0
        product = self.env['product.product'].browse(productid).with_company(self.env.company)
        ctx = {'warehouse_id': warehouseid}
        if self.env.context.get('to_date'):
            ctx['to_date'] = fields.Datetime.to_datetime(self.env.context['to_date'])
        return product.with_context(**ctx).qty_available

    def _sh_get_warehouse_cost_line(self, product, warehouse):
        return product.warehouse_cost_lines.filtered(
            lambda x: x.warehouse_id == warehouse)[:1]

    def _sh_set_warehouse_cost(self, product, warehouse, cost):
        """Create or update the warehouse cost bucket for ``product``/``warehouse``."""
        line = self._sh_get_warehouse_cost_line(product, warehouse)
        if line:
            line.cost = cost
        else:
            self.env['sh.warehouse.cost'].create({
                'product_id': product.id,
                'warehouse_id': warehouse.id,
                'cost': cost,
            })

    # ------------------------------------------------------------------
    # Warehouse cost maintenance
    # ------------------------------------------------------------------
    def _sh_update_incoming_warehouse_cost(self):
        """Blend the destination warehouse average cost with a received quantity.

        Replaces the old ``product_price_update_before_done`` / ``_get_in_svl_vals``
        logic. Uses the move value computed by Odoo core (purchase price, returns,
        landed cost, ...).
        """
        self.ensure_one()
        warehouse = self.location_dest_id.warehouse_id
        if not warehouse:
            return
        product = self.product_id.with_company(self.company_id)
        in_qty = self._get_valued_qty()
        if product.uom_id.is_zero(in_qty):
            return
        in_unit_cost = abs(self.value) / in_qty if in_qty else 0.0
        # The move is already done so ``qty_available`` already includes ``in_qty``.
        prior_qty = self.get_quantity_from_valuation(product.id, warehouse.id) - in_qty
        line = self._sh_get_warehouse_cost_line(product, warehouse)
        prior_cost = line.cost if line else 0.0
        total_qty = prior_qty + in_qty
        if total_qty > 0:
            new_cost = ((prior_cost * prior_qty) + (in_unit_cost * in_qty)) / total_qty
        else:
            new_cost = in_unit_cost
        self._sh_set_warehouse_cost(product, warehouse, new_cost)

    def _sh_transfer_warehouse_cost(self):
        """Move warehouse cost from the source bucket to the destination bucket for
        an internal transfer between two different warehouses.

        Removing quantity from the source at its own average leaves the source
        average unchanged, so only the destination needs to be re-averaged.
        """
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        src_wh = self.location_id.warehouse_id
        dst_wh = self.location_dest_id.warehouse_id
        # Internal moves are not in/out (both sides valued) so ``_get_valued_qty``
        # returns 0: compute the moved quantity directly.
        qty = self.product_uom._compute_quantity(self.quantity, product.uom_id)
        if product.uom_id.is_zero(qty):
            return
        src_line = self._sh_get_warehouse_cost_line(product, src_wh)
        unit_cost = src_line.cost if src_line else product.standard_price
        # Ensure the source bucket exists (its cost is unchanged by the outflow).
        if not src_line and src_wh:
            self._sh_set_warehouse_cost(product, src_wh, unit_cost)
        # Re-average the destination bucket.
        dst_line = self._sh_get_warehouse_cost_line(product, dst_wh)
        dst_prior_qty = self.get_quantity_from_valuation(product.id, dst_wh.id) - qty
        dst_prior_cost = dst_line.cost if dst_line else 0.0
        dst_total = dst_prior_qty + qty
        new_dst_cost = (((dst_prior_cost * dst_prior_qty) + (unit_cost * qty)) / dst_total
                        if dst_total > 0 else unit_cost)
        self._sh_set_warehouse_cost(product, dst_wh, new_dst_cost)

    # ------------------------------------------------------------------
    # Overrides of the new Odoo 19 valuation entry points
    # ------------------------------------------------------------------
    def _set_value(self, correction_quantity=None):
        """Value outgoing AVCO moves at the source warehouse cost.

        This is the new home of the old ``_prepare_out_svl_vals`` warehouse
        override. Odoo computes the global average for the standard price from the
        *incoming* move values only, so overriding the outgoing ``value`` here does
        not disturb the global standard price recomputation done by ``super``.
        """
        res = super()._set_value(correction_quantity=correction_quantity)
        if correction_quantity:
            return res
        for move in self:
            product = move.product_id
            if product.cost_method != 'average' or product.lot_valuated:
                continue
            if not move._is_out():
                continue
            warehouse = move.location_id.warehouse_id
            if not warehouse:
                continue
            line = move._sh_get_warehouse_cost_line(
                product.with_company(move.company_id), warehouse)
            if line and line.cost:
                move.value = line.cost * move._get_valued_qty()
        return res

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        for move in res:
            product = move.product_id
            if product.cost_method != 'average' or product.lot_valuated:
                continue
            # Genuine incoming move (receipt, customer return, ...).
            if move.is_in:
                move._sh_update_incoming_warehouse_cost()
                continue
            # Internal transfer between two distinct warehouses.
            if (move.picking_type_id.code == 'internal'
                    and move.location_id.warehouse_id
                    and move.location_dest_id.warehouse_id
                    and move.location_id.warehouse_id != move.location_dest_id.warehouse_id):
                move._sh_transfer_warehouse_cost()
        return res
