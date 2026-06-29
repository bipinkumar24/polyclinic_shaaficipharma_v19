# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
#
# Odoo 19 migration note
# ----------------------
# ``_prepare_out_svl_vals`` and ``_stock_account_get_anglo_saxon_price_unit`` no
# longer exist in Odoo 19 (the whole ``stock.valuation.layer`` engine was removed).
# Outgoing valuation at the warehouse cost is now done in
# ``stock.move._set_value`` (see ``stock_move.py``); since the COGS is derived from
# the stock move value, the warehouse-wise COGS keeps working without the old
# anglo-saxon override.

from odoo import fields, models, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    can_edit_warehouse_cost = fields.Boolean(
        compute="_compute_can_edit_warehouse_cost",
        store=False
    )

    warehouse_cost_lines = fields.One2many('sh.warehouse.cost', 'product_id')

    def _compute_can_edit_warehouse_cost(self):
        has_group = self.env.user.has_group(
            'sh_warehouse_avg_costing.group_warehouse_cost_edit'
        )
        for record in self:
            record.can_edit_warehouse_cost = has_group

    def get_warehouse_wise_cost(self, warehouse_id):
        return self.warehouse_cost_lines.filtered(lambda x: x.warehouse_id.id == warehouse_id)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    warehouse_cost_lines = fields.One2many('sh.warehouse.cost', 'product_id', compute='_compute_warehouse_cost_lines', inverse='_set_warehouse_cost_lines')
    can_edit_warehouse_cost = fields.Boolean(
        compute="_compute_can_edit_warehouse_cost",
        store=False
    )

    def _compute_can_edit_warehouse_cost(self):
        has_group = self.env.user.has_group(
            'sh_warehouse_avg_costing.group_warehouse_cost_edit'
        )
        for record in self:
            record.can_edit_warehouse_cost = has_group

    @api.depends('product_variant_ids.warehouse_cost_lines')
    def _compute_warehouse_cost_lines(self):
        self._compute_template_field_from_variant_field('warehouse_cost_lines')

    def _set_warehouse_cost_lines(self):
        self._set_product_variant_field('warehouse_cost_lines')
