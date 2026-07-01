# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, api


class SaleOrderMargin(models.Model):
    """ Sale Order Margin """
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom_id', 'order_id.warehouse_id')
    def _compute_purchase_price(self):
        for line in self:
            if not line.product_id:
                line.purchase_price = 0.0
                continue
            line = line.with_company(line.company_id)

            # Convert the cost to the line UoM
            product_cost = line.product_id.warehouse_cost_lines.filtered(
                lambda x: x.warehouse_id.id == self.order_id.warehouse_id.id).cost
            if not product_cost:
                product_cost = line.product_id.uom_id._compute_price(
                    line.product_id.standard_price,
                    line.product_uom_id,
                )
            line.purchase_price = line._convert_to_sol_currency(
                product_cost,
                line.product_id.cost_currency_id)
