# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, api


class ProductValue(models.Model):
    _inherit = 'product.value'

    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Warehouse", required=True)

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('from_warehouse_revaluation'):
            return super().create(vals_list)

        lot_ids = set()
        product_ids = set()
        move_ids = set()

        for vals in vals_list:
            if vals.get('move_id'):
                move_ids.add(vals['move_id'])
            elif vals.get('lot_id'):
                lot_ids.add(vals['lot_id'])
            else:
                product_ids.add(vals['product_id'])
        
        if lot_ids:
            moves = self.env['stock.move'].search([('lot_id', 'in', list(lot_ids))])
            if self.warehouse_id:
                moves = moves.filtered(lambda m: m.location_id.warehouse_id == self.warehouse_id or m.location_dest_id.warehouse_id == self.warehouse_id)
            move_ids.update(moves.ids)

        products = self.env['product.product'].browse(product_ids)
        if products:
            # moves_by_product = products._get_remaining_moves(warehouse_id=self.warehouse_id.id)
            moves_by_product = products._get_remaining_moves()
            for qty_by_move in moves_by_product.values():
                move_ids.update(self.env['stock.move'].concat(*qty_by_move.keys()).ids)

        res = super(ProductValue, self.with_context(from_warehouse_revaluation=True)).create(vals_list)
        
        if move_ids:
            self.env['stock.move'].browse(move_ids)._set_value()
        
        # Custom logic to update warehouse cost
        for vals in vals_list:
            product = self.env['product.product'].browse(vals.get('product_id'))
            warehouse = self.env['stock.warehouse'].browse(vals.get('warehouse_id'))
            added_value = vals.get('value', 0)
            
            if product and warehouse and added_value:
                warehouse_cost_line = product.warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id == warehouse)
                
                group_quantity = self.get_quantity_from_valuation(
                    product.id, warehouse.id)
                
                if warehouse_cost_line:
                    warehouse_cost = warehouse_cost_line.cost
                    if group_quantity > 0:
                        warehouse_cost += added_value / group_quantity
                    else:
                        warehouse_cost += added_value
                    warehouse_cost_line.cost = warehouse_cost
                else:
                    cost = product.standard_price
                    if group_quantity > 0:
                        cost += added_value / group_quantity
                    else:
                        cost += added_value
                    self.env['sh.warehouse.cost'].create({
                        'product_id': product.id,
                        'warehouse_id': warehouse.id,
                        'cost': cost,
                    })

        return res

    def get_quantity_from_valuation(self, productid, warehouseid):
        """Get quantity from stock.quant for a specific warehouse."""
        company_id = self.env.company.id
        domain = [('product_id', '=', productid),
                  ('company_id', '=', company_id),
                  ('location_id.warehouse_id', '=', warehouseid)]
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
