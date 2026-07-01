# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from collections import defaultdict
from odoo import fields, models, api
from odoo.tools.float_utils import float_round, float_is_zero, float_compare


class WarehouseStockMove(models.Model):
    """Warehouse Stock Move"""
    _inherit = "stock.move"

    sh_in_replenshment = fields.Boolean("Is Replenishment")

    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self._should_ignore_pol_price():
            self.ensure_one()
            price_unit = self.price_unit
            precision = self.env['decimal.precision'].precision_get('Product Price')
            # If the move is a return, use the original move's price unit.
            if self.origin_returned_move_id and self.origin_returned_move_id.sudo().stock_valuation_layer_ids:
                layers = self.origin_returned_move_id.sudo().stock_valuation_layer_ids
                # dropshipping create additional positive svl to make sure there is no impact on the stock valuation
                # We need to remove them from the computation of the price unit.
                if self.origin_returned_move_id._is_dropshipped() or self.origin_returned_move_id._is_dropshipped_returned():
                    layers = layers.filtered(
                        lambda l: float_compare(l.value, 0, precision_rounding=l.product_id.uom_id.rounding) <= 0)
                layers |= layers.stock_valuation_layer_ids
                if self.product_id.lot_valuated:
                    layers_by_lot = layers.grouped('lot_id')
                    prices = {}
                    for lot, stock_layers in layers_by_lot.items():
                        qty = sum(stock_layers.mapped("quantity"))
                        val = sum(stock_layers.mapped("value"))
                        prices[lot] = val / qty if not float_is_zero(qty,
                                                                     precision_rounding=self.product_id.uom_id.rounding) else 0
                else:
                    quantity = sum(layers.mapped("quantity"))
                    prices = {
                        self.env['stock.lot']: sum(layers.mapped("value")) / quantity if not float_is_zero(quantity,
                                                                                                           precision_rounding=layers.uom_id.rounding) else 0}
                return prices
            # Custom Code update cost price as per warehouse rather than product standard price
            price = self.product_id.warehouse_cost_lines.filtered(
                lambda x: x.warehouse_id.id == self.location_dest_id.warehouse_id.id).cost
            if price:
                return {self.env['stock.lot']: price}
            # Custom Code update cost price as per warehouse rather than product standard price
            if not float_is_zero(price_unit, precision) or self._should_force_price_unit():
                if self.product_id.lot_valuated:
                    return dict.fromkeys(self.lot_ids, price_unit)
                else:
                    return {self.env['stock.lot']: price_unit}
            else:
                if self.product_id.lot_valuated:
                    return {lot: lot.standard_price or self.product_id.standard_price for lot in self.lot_ids}
                else:
                    return {self.env['stock.lot']: self.product_id.standard_price}
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        line = self.purchase_line_id
        order = line.order_id
        received_qty = line.qty_received
        if self.state == 'done':
            received_qty -= self.product_uom._compute_quantity(self.quantity, line.product_uom_id,
                                                               rounding_method='HALF-UP')
        if line.product_id.purchase_method == 'purchase' and float_compare(line.qty_invoiced, received_qty,
                                                                           precision_rounding=line.product_uom_id.rounding) > 0:
            move_layer = line.move_ids.sudo().stock_valuation_layer_ids
            invoiced_layer = line.sudo().invoice_lines.stock_valuation_layer_ids
            # value on valuation layer is in company's currency, while value on invoice line is in order's currency
            receipt_value = 0
            if move_layer:
                receipt_value += sum(move_layer.mapped(lambda l: l.currency_id._convert(
                    l.value, order.currency_id, order.company_id, l.create_date, round=False)))
            if invoiced_layer:
                receipt_value += sum(invoiced_layer.mapped(lambda l: l.currency_id._convert(
                    l.value, order.currency_id, order.company_id, l.create_date, round=False)))
            total_invoiced_value = 0
            invoiced_qty = 0
            for invoice_line in line.sudo().invoice_lines:
                if invoice_line.move_id.state != 'posted':
                    continue
                # Adjust unit price to account for discounts before adding taxes.
                adjusted_unit_price = invoice_line.price_unit * (
                            1 - (invoice_line.discount / 100)) if invoice_line.discount else invoice_line.price_unit
                if invoice_line.tax_ids:
                    invoice_line_value = invoice_line.tax_ids.compute_all(
                        adjusted_unit_price,
                        currency=invoice_line.currency_id,
                        quantity=invoice_line.quantity,
                        rounding_method="round_globally",
                    )['total_void']
                else:
                    invoice_line_value = adjusted_unit_price * invoice_line.quantity
                total_invoiced_value += invoice_line.currency_id._convert(
                    invoice_line_value, order.currency_id, order.company_id, invoice_line.move_id.invoice_date,
                    round=False)
                invoiced_qty += invoice_line.product_uom_id._compute_quantity(invoice_line.quantity,
                                                                              line.product_id.uom_id)
            # TODO currency check
            remaining_value = total_invoiced_value - receipt_value
            # TODO qty_received in product uom
            remaining_qty = invoiced_qty - line.product_uom_id._compute_quantity(received_qty, line.product_id.uom_id)
            if order.currency_id != order.company_id.currency_id and remaining_value and remaining_qty:
                # will be rounded during currency conversion
                price_unit = remaining_value / remaining_qty
            elif remaining_value and remaining_qty:
                price_unit = float_round(remaining_value / remaining_qty, precision_digits=price_unit_prec)
            else:
                price_unit = line._get_gross_price_unit()
        else:
            price_unit = line._get_gross_price_unit()
        if order.currency_id != order.company_id.currency_id:
            # The date must be today, and not the date of the move since the move move is still
            # in assigned state. However, the move date is the scheduled date until move is
            # done, then date of actual move processing. See:
            # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
            price_unit = order.currency_id._convert(
                price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self),
                round=False)
        if self.product_id.lot_valuated:
            return dict.fromkeys(self.lot_ids, price_unit)
        return {self.env['stock.lot']: price_unit}

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, description):
        """
        Generate the account move line values.
        """
        self.ensure_one()

        if self.product_id.valuation != 'real_time':
            return []

        move_line_values = {
            'name': description or self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_uom.id,
            'ref': self.picking_id.name,
            'partner_id': self.partner_id.id,
            'debit': cost > 0 and cost or 0,
            'credit': cost < 0 and -cost or 0,
            'account_id': cost > 0 and debit_account_id or credit_account_id,
        }
        return [(0, 0, move_line_values)]


    def _action_done(self, cancel_backorder=False):
        # * Softhealer code Start *

        # Called Super used to create svl when internal transfer is done

        # * Softhealer code end *
        if self:
            tmpl_dict = defaultdict(lambda: 0.0)
            for move in self.filtered(lambda move: move._is_in() and move.with_company(move.company_id).product_id.cost_method == 'average'):
                group_quantity = self.get_quantity_from_valuation(
                    move.product_id.id, move.location_dest_id.warehouse_id.id) + tmpl_dict[move.product_id.id]
                valued_move_lines = move._get_in_move_lines()
                qty_done = 0
                for valued_move_line in valued_move_lines:
                    qty_done += valued_move_line.product_uom_id._compute_quantity(
                        valued_move_line.quantity, move.product_id.uom_id)
                qty =  qty_done
                amount_unit = 0.0
                warehouse = False
                warehouse = move.product_id.with_company(move.company_id).warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == move.location_dest_id.warehouse_id.id)
                price_unit_result = move._get_price_unit()
                if isinstance(price_unit_result, dict):
                    sh_new_std_price = next(iter(price_unit_result.values()))
                else:
                    sh_new_std_price = price_unit_result
                sh_sum_qty=group_quantity + qty # sh for division error
                if warehouse:
                    amount_unit = warehouse.cost
                    if sh_sum_qty!=0:
                        new_std_price = ((amount_unit * group_quantity) +
                                     (sh_new_std_price * qty)) / sh_sum_qty
                    else:
                        new_std_price=0
                    warehouse.write({'cost': new_std_price})
                else:
                    if sh_sum_qty!=0:
                        new_std_price = ((amount_unit * group_quantity) +
                                     (sh_new_std_price * qty)) / sh_sum_qty
                    else:
                        new_std_price=0
                    self.env['sh.warehouse.cost'].create({
                        'product_id': move.product_id.id,
                        'warehouse_id': move.location_dest_id.warehouse_id.id,
                        'cost': new_std_price
                    })
                tmpl_dict[move.product_id.id] += qty_done
        for rec in self:
            if rec.sh_in_replenshment and rec.picking_id.group_id:
                qty = rec.quantity
                amount_unit = 0.0
                warehouse = False
                warehouse = rec.product_id.with_company(rec.company_id).warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == rec.picking_id.location_dest_id.warehouse_id.id)
                source_picking = self.env['stock.picking'].search([('origin','=',rec.picking_id.group_id.name)])
                source_warehouse = rec.product_id.with_company(rec.company_id).warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == source_picking.location_id.warehouse_id.id)
                sh_sum_qty=warehouse.sh_onhand_qty + qty #sh for division error
                if warehouse:
                    amount_unit = warehouse.cost
                    if sh_sum_qty!=0:
                        new_std_price = ((amount_unit * warehouse.sh_onhand_qty) +
                                        (source_warehouse.cost * qty)) / sh_sum_qty
                    else:
                        new_std_price=0
                    warehouse.write({'cost': new_std_price})
                elif source_warehouse:
                    source_Warehouse_cost = 0.0
                    if source_warehouse:
                        source_Warehouse_cost = source_warehouse.cost
                    if sh_sum_qty!=0:
                        new_std_price = ((amount_unit * warehouse.sh_onhand_qty) +
                                        (source_Warehouse_cost)) / sh_sum_qty
                    else:
                        new_std_price=0
                    self.env['sh.warehouse.cost'].create({
                        'product_id': rec.product_id.id,
                        'warehouse_id': rec.picking_id.location_dest_id.warehouse_id.id,
                        'cost': new_std_price
                    })
        res = super(WarehouseStockMove, self)._action_done(cancel_backorder)
        for rec in self:
            if rec.picking_type_id.code == 'internal':
                if rec.location_id.warehouse_id.id != rec.location_dest_id.warehouse_id.id:
                    rec.create_manually_svl_in_out_vals()
        return res

    def create_manually_svl_in_out_vals(self):
        # * Softhealer code Start *

        # Update warehouse wise price when internal transfer is made and added in and out svl lines

        # * Softhealer code end *
        for move in self:
            for lines in move.move_line_ids:
                price = lines.product_id.warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == move.location_id.warehouse_id.id).cost
                group_quantity = self.get_quantity_from_valuation(
                    move.product_id.id, move.location_dest_id.warehouse_id.id)
                group_quantity_from = self.get_quantity_from_valuation(
                    move.product_id.id, move.location_id.warehouse_id.id)
                amount_unit = 0.0
                amount_unit_from = 0.0
                warehouse = False
                warehouse_from = False
                warehouse = move.product_id.with_company(move.company_id).warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == move.location_dest_id.warehouse_id.id)
                warehouse_from = move.product_id.with_company(move.company_id).warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == move.location_id.warehouse_id.id)
                valued_quantity = 0
                valued_quantity = lines.product_uom_id._compute_quantity(
                    lines.quantity, move.product_id.uom_id)
                # valued_quantity = lines.product_uom_id._compute_quantity(
                #     lines.qty_done, move.product_id.uom_id)
                if warehouse_from:
                    amount_unit_from = warehouse_from.cost
                    if group_quantity_from - valued_quantity == 0:
                        new_std_price_from = (
                            (amount_unit_from * group_quantity_from) - (price * valued_quantity))
                    else:
                        new_std_price_from = (
                            (amount_unit_from * group_quantity_from) - (price * valued_quantity)) / (group_quantity_from - valued_quantity)
                    warehouse_from.write({'cost': new_std_price_from})
                if warehouse:
                    amount_unit = warehouse.cost
                    if group_quantity + valued_quantity == 0:
                        new_std_price = (
                            (amount_unit * group_quantity) + (price * valued_quantity))
                    else:
                        new_std_price = (
                            (amount_unit * group_quantity) + (price * valued_quantity)) / (group_quantity + valued_quantity)
                    warehouse.write({'cost': new_std_price})
                else:
                    self.env['sh.warehouse.cost'].create({
                        'product_id': move.product_id.id,
                        'warehouse_id': self.location_dest_id.warehouse_id.id,
                        'cost': price
                    })


    def get_quantity_from_valuation(self, productid, warehouseid):
        """
        Get quantity from stock.move for a specific warehouse.
        """
        company_id = self.env.company.id
        domain = [('product_id', '=', productid), ('company_id', '=', company_id), ('state', '=', 'done')]
        if self.env.context.get('to_date'):
            domain.append(('date', '<=', fields.Datetime.to_datetime(self.env.context['to_date'])))
        qty_in = 0.0
        domain_in = domain + [('location_dest_id.warehouse_id', '=', warehouseid)]
        moves_in = self.env['stock.move'].read_group(domain_in, ['quantity:sum'], ['product_id'])
        qty_in = moves_in[0]['quantity'] if moves_in and moves_in[0]['quantity'] else 0
        qty_out = 0.0
        if not qty_in:
            domain_out = domain + [('location_id.warehouse_id', '=', warehouseid)]
            moves_out = self.env['stock.move'].read_group(domain_out, ['quantity:sum'], ['product_id'])
            qty_out = moves_out[0]['quantity'] if moves_out and moves_out[0]['quantity'] else 0

        return qty_in - qty_out