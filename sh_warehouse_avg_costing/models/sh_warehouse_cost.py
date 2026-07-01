# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class WarehouseCosting(models.Model):
    """Warehouse Costing"""
    _name = "sh.warehouse.cost"
    _description = "Stores Cost warehouse Wise"

    product_id = fields.Many2one('product.product', string="Product")
    warehouse_id = fields.Many2one('stock.warehouse')
    cost = fields.Float("Cost")
    sh_onhand_qty = fields.Float(
        "Onhand Quantity", compute="_compute_onhand_warehouse_wise")

    company_id = fields.Many2one('res.company', related="warehouse_id.company_id", store=True)

    def _compute_onhand_warehouse_wise(self):
        for rec in self:
            rec.sh_onhand_qty = 0.0
            if rec.warehouse_id:
                quantity = sum(
                    self.env['stock.quant'].search([
                        ('product_id', '=', rec.product_id.id)
                    ]).filtered(lambda x: x.location_id.warehouse_id.id ==
                                rec.warehouse_id.id).mapped('quantity'))
                rec.sh_onhand_qty = quantity
