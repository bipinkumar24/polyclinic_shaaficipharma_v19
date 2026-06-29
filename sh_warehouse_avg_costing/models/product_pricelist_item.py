# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    base = fields.Selection(
        selection_add=[
            ('warehouse_cost', 'Warehouse Cost')
        ],
        ondelete={'warehouse_cost': 'set default'},
    )

    def _compute_base_price(self, product, quantity, uom, date, currency, **kwargs):
        # Odoo 19: ``_compute_base_price`` now accepts ``**kwargs`` and operates on a
        # single rule, returning the base price (expressed in ``currency``).
        self.ensure_one()
        if self.base != 'warehouse_cost':
            return super()._compute_base_price(product, quantity, uom, date, currency, **kwargs)
        warehouse = self.env.context.get('x_warehouse_for_sh_cost')
        warehouse_cost = product.get_warehouse_wise_cost(warehouse)
        price = warehouse_cost[0].cost if warehouse_cost else 1.0
        src_currency = product.cost_currency_id
        if src_currency and src_currency != currency:
            price = src_currency._convert(price, currency, self.env.company, date, round=False)
        return price
