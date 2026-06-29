# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, api


class SaleOrderMargin(models.Model):
    _inherit = 'sale.order.line'

    # Odoo 19: the unit-of-measure field on sale.order.line is ``product_uom_id``.
    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom_id', 'order_id.warehouse_id')
    def _compute_purchase_price(self):
        for line in self:
            if not line.product_id:
                line.purchase_price = 0.0
                continue
            line = line.with_company(line.company_id)

            # Use the warehouse-wise cost of the order's warehouse when available,
            # otherwise fall back to the product standard price.
            warehouse = line.order_id.warehouse_id
            warehouse_cost = line.product_id.warehouse_cost_lines.filtered(
                lambda x: x.warehouse_id == warehouse) if warehouse else line.product_id.warehouse_cost_lines.browse()
            cost = warehouse_cost[:1].cost if warehouse_cost else line.product_id.standard_price

            # Convert the cost to the line UoM
            product_cost = line.product_id.uom_id._compute_price(cost, line.product_uom_id)
            line.purchase_price = line._convert_to_sol_currency(
                product_cost,
                line.product_id.cost_currency_id)
