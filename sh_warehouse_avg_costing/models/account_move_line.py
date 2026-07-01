# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models


class WarehouseAccountMoveLine(models.Model):
    """Warehouse Account Move Line"""
    _inherit = 'account.move.line'

    def _stock_account_get_anglo_saxon_price_unit(self):
        """Stock Account Get Anglo Saxon Price Unit"""
        self.ensure_one()
        warehouse = False
        if self.move_id.invoice_origin:
            domain = [('name', '=', self.move_id.invoice_origin)]
            sale_order = self.env['sale.order'].search(domain)
            if sale_order:
                warehouse = sale_order.warehouse_id.id
        if not self.product_id:
            return self.price_unit
        original_line = self.move_id.reversed_entry_id.line_ids.filtered(
            lambda l: l.display_type == 'cogs' and l.product_id ==
            self.product_id and l.product_uom_id == self.product_uom_id and
            l.price_unit >= 0)
        original_line = original_line and original_line[0]
        if original_line:
            return original_line.price_unit
        return self.product_id.with_company(
            self.company_id)._stock_account_get_anglo_saxon_price_unit(
                uom=self.product_uom_id, warehouse=warehouse)
