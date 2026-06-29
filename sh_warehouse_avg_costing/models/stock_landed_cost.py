# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
#
# Odoo 19 migration note
# ----------------------
# In Odoo 19 ``stock.landed.cost.button_validate`` no longer creates
# ``stock.valuation.layer`` records: the additional landed cost is added to the
# stock move value through ``stock.move._get_value_from_extra`` and the account
# entries / standard price recomputation are handled by core. We therefore call
# ``super()`` and only propagate the additional cost to the warehouse-wise average
# cost buckets afterwards.

from odoo import models
from collections import defaultdict


class WarehouseLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def button_validate(self):
        res = super().button_validate()
        StockMove = self.env['stock.move']
        for cost in self:
            cost = cost.with_company(cost.company_id)
            add_by_product_wh = defaultdict(float)
            for line in cost.valuation_adjustment_lines.filtered(lambda l: l.move_id):
                product = line.move_id.product_id
                if product.cost_method != 'average':
                    continue
                warehouse = line.move_id.location_dest_id.warehouse_id
                if not warehouse:
                    continue
                qty = line.quantity or line.move_id.product_qty
                # Prorate the landed cost on what is still in stock, like the
                # original module did.
                remaining_qty = line.move_id.remaining_qty
                cost_to_add = (remaining_qty / qty) * line.additional_landed_cost if qty else 0.0
                add_by_product_wh[(product, warehouse)] += cost_to_add

            for (product, warehouse), value in add_by_product_wh.items():
                if cost.company_id.currency_id.is_zero(value):
                    continue
                wh_qty = StockMove.get_quantity_from_valuation(product.id, warehouse.id)
                wh_line = product.warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id == warehouse)[:1]
                if wh_line and wh_qty:
                    wh_line.cost += value / wh_qty
        return res
