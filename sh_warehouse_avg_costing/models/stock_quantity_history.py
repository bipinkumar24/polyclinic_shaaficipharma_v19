# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
#
# Odoo 19 migration note
# ----------------------
# ``stock.quantity.history.open_at_date`` no longer opens a
# ``stock.valuation.layer`` action (the model was removed). It now opens the
# product list with a ``to_date`` context so that the valuation is computed at the
# chosen date by the native engine. We simply inject the selected warehouse into
# the context so the at-date quantities/values are restricted to that warehouse.

from odoo import fields, models


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    def open_at_date(self):
        action = super().open_at_date()
        if self.warehouse_id and isinstance(action, dict) and action.get('context') is not None:
            action['context'] = dict(action['context'], warehouse_id=self.warehouse_id.id)
        return action
