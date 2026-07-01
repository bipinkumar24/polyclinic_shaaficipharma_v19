# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models, _
from odoo.tools.misc import format_datetime


class StockQuantityHistory(models.TransientModel):
    """Stock Quantity History"""
    _inherit = 'stock.quantity.history'

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    def open_at_date(self):
        """Open at date"""
        action = super().open_at_date()
        if self.warehouse_id:
            product_ids = self.env['product.product'].search([('type', '=', 'storable')]).with_context(warehouse=self.warehouse_id.id).filtered(lambda p: p.qty_available != 0)
            action['domain'] = [('id', 'in', product_ids.ids)]
            action['display_name'] = _('Products in %s at %s') % (self.warehouse_id.name, format_datetime(self.env, self.inventory_datetime))
        return action