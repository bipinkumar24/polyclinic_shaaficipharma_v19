# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from collections import defaultdict
from odoo import fields, models, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError


class WarehouseLandedCost(models.Model):
    """
    Warehouse Landed Cost
    """
    _inherit = 'stock.landed.cost'

    def button_validate(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'move_type': 'entry',
            }
            cost_to_add_byproduct = defaultdict(lambda: 0.0)
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                product = line.move_id.product_id
                # Products with manual inventory valuation are ignored because they do not need to create journal entries.
                if product.valuation != "real_time":
                    continue

                remaining_qty = line.move_id.remaining_qty

                # Prorate the value at what's still in stock
                cost_to_add = (
                    remaining_qty / line.move_id.product_qty
                ) * line.additional_landed_cost if line.move_id.product_qty else line.additional_landed_cost

                if product.cost_method == 'average':
                    cost_to_add_byproduct[product] += cost_to_add

                move_vals['line_ids'] += line._create_accounting_entries(remaining_qty)

            products = self.env['product.product'].browse(
                p.id for p in cost_to_add_byproduct.keys())

            temp_warehouse = []
            for picking in cost.picking_ids:
                warehouse = picking.location_dest_id.warehouse_id
                if warehouse not in temp_warehouse:
                    temp_warehouse.append(warehouse)
                    for product in products:
                        group_quantity = self.get_quantity_from_valuation(
                            product.id, warehouse.id)
                        if group_quantity > 0:
                            change_warehouse = product.warehouse_cost_lines.filtered(
                                lambda x: x.warehouse_id.id == warehouse.id)
                            if change_warehouse:
                                change_warehouse.cost += cost_to_add_byproduct[
                                    product] / group_quantity

            cost_vals = {'state': 'done'}
            if move_vals.get("line_ids"):
                move = move.create(move_vals)
                cost_vals.update({'account_move_id': move.id})
            cost.write(cost_vals)
            if cost.account_move_id:
                move._post()

            cost.valuation_adjustment_lines.move_id._set_value()

        return True

    def get_quantity_from_valuation(self, productid, warehouseid):
        """
        New Method (accepts the product and warehouse and returns the
        quantity warehouse wise from stock quant)
        """
        company_id = self.env.company.id
        domain = [
            ('product_id', '=', productid),
            ('company_id', '=', company_id),
            ('location_id.warehouse_id', '=', warehouseid)
        ]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(
                self.env.context['to_date'])
            domain.append(('in_date', '<=', to_date))

        groups = self.env['stock.quant'].read_group(
            domain, ['quantity:sum'], ['product_id'])
        if groups:
            for group in groups:
                return group['quantity']
        return 0
