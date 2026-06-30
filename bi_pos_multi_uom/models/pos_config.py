# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from itertools import groupby
_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
	_inherit = 'pos.config'

	product_multi_uom = fields.Boolean(string="Product Multi UOM")


class PosOrder(models.Model):
	_inherit = 'pos.order'

	uom = fields.Boolean(string="uom", related='config_id.product_multi_uom', readonly=True)

	@api.model
	def _get_invoice_lines_values(self, line_values, pos_line, move_type):
		# v19: the base signature gained `move_type` and now handles the refund
		# quantity sign and extra tax data. Keep all core behaviour and only
		# override the invoice line UoM when a second (multi) UoM was selected
		# on the POS order line.
		vals = super()._get_invoice_lines_values(line_values, pos_line, move_type)
		custom_uom_name = pos_line.custom_uom_id
		if custom_uom_name and custom_uom_name != 'Units':
			second_uom_id = pos_line.second_uom_id
			if second_uom_id and second_uom_id.factor:
				vals['product_uom_id'] = second_uom_id.id
		return vals

	def action_rebuild_picking(self):
		for order in self:
			pickings = order.picking_ids

			if any(p.state == 'done' for p in pickings):
				raise UserError("Picking already done")

			# 1. Cancel & delete existing pickings
			pickings.action_cancel()
			pickings.unlink()

			# 2. Recreate picking using POS internal logic
			order._create_order_picking()

class PosOrderLine(models.Model):
	_inherit = 'pos.order.line'

	uom_id = fields.Many2one('uom.uom', string="Unit Of Measure")
	custom_uom_id = fields.Char(string =" Units of Measure")
	second_uom_id = fields.Many2one('uom.uom',compute='_compute_second_uom_id')
	custom_uom_number_id = fields.Char(string =" ggg")
	custom_qty = fields.Float()

	@api.depends('custom_uom_id')
	def _compute_second_uom_id(self):
		for rec in self:
			if rec.custom_uom_id:
				uom = self.env['uom.uom'].sudo().search([('id','=',rec.custom_uom_number_id)])
				rec.second_uom_id = uom.id
				# rec.custom_qty = rec.qty * uom.factor_inv
			else:
				rec.second_uom_id = False
				# rec.custom_qty = rec.qty
	
	def _compute_total_cost(self, stock_moves):
		"""
		Compute the total cost of the order lines.
		Override to use custom_qty when multi-UOM is enabled.
		:param stock_moves: recordset of `stock.move`, used for fifo/avco lines
		"""
		for line in self.filtered(lambda l: not l.is_total_cost_computed):
			product = line.product_id
			
			if line.order_id.config_id.product_multi_uom and line.custom_qty:
				quantity_to_use = line.custom_qty
			else:
				quantity_to_use = line.qty
				
			if line._is_product_storable_fifo_avco() and stock_moves:
				product_cost = product._compute_average_price(0, quantity_to_use, line._get_stock_moves_to_consider(stock_moves, product))
				if (product.cost_currency_id.is_zero(product_cost) and line.order_id.shipping_date and line.refunded_orderline_id):
					product_cost = line.refunded_orderline_id.total_cost / line.refunded_orderline_id.qty
			else:
				product_cost = product.standard_price
				
			line.total_cost = quantity_to_use * product.cost_currency_id._convert(
				from_amount=product_cost,
				to_currency=line.currency_id,
				company=line.company_id or self.env.company,
				date=line.order_id.date_order or fields.Date.today(),
				round=False,
			)
			line.is_total_cost_computed = True

	@api.model
	def _load_pos_data_fields(self, config_id):
		params = super()._load_pos_data_fields(config_id)
		params += ['uom_id','custom_uom_id','custom_qty','custom_uom_number_id']
		return params

	def _order_line_fields(self, line, session_id=None):
		result = super()._order_line_fields(line, session_id)
		vals = result[2]
		if vals.get('uom_id', False):
			vals['uom_id'] = vals['uom_id']
		return result

	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			try:
				if vals.get('uom_id'):
					vals['uom_id'] = vals.get('uom_id')[0]
				if vals.get('custom_uom_id'):
					uom = self.env['uom.uom'].sudo().search([('id','=',vals.get('custom_uom_number_id'))])
					# v19: uom.uom.factor_inv was removed; `factor` is now the
					# absolute quantity in reference units (== v18 factor_inv).
					vals['custom_qty'] = vals['qty'] * uom.factor
				else:
					vals['custom_qty'] = vals['qty']

			except Exception:
				vals['uom_id'] = vals.get('uom_id') or None
				pass
		res = super(PosOrderLine, self).create(vals_list)
		return res

  

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	product_uom_ids = fields.One2many('product.template.uom.line', 'product_uom_line_id', string="discard Lines")
	point_of_sale_uom = fields.Boolean(string="Point Of Sale UOM")

	@api.onchange('point_of_sale_uom', 'uom_id', 'list_price')
	def _onchange_point_of_sale_uom(self):
		# Odoo 19 removed the `uom.category` model along with `uom_type` and
		# `uom.uom.factor_inv`, and the `auto_calculate_sale_price` flag lived on
		# that category. The automatic pre-fill of the POS UoM price lines is
		# therefore no longer available. Multi-UoM lines are now entered manually
		# in the "Point Of Sale UOM" table; this onchange is kept as a no-op so
		# manually entered lines are preserved and nothing references the removed
		# fields.
		return

	
class ProductProduct(models.Model):
	_inherit = 'product.product'

	# product_uom_ids = fields.One2many('product.template.uom.line', 'product_uom_line_id', string="discard Lines")
	# point_of_sale_uom = fields.Boolean(string="Point Of Sale UOM")

	@api.model
	def _load_pos_data_fields(self, config_id):
		params = super()._load_pos_data_fields(config_id)
		params += ['point_of_sale_uom', 'product_uom_ids']
		return params


class ProductTemplateUomLine(models.Model):
	_name = 'product.template.uom.line'
	_inherit = ['pos.load.mixin']
	_description = "Point of Sale Product UOM"

	product_uom_line_id = fields.Many2one('product.template', string="Product UOM")
	unit_of_measure_id = fields.Many2one('uom.uom', string="Unit Of Measure")
	sale_price = fields.Float(string="Sale Price", compute="_compute_list_price", store=True, digits=(16, 3))

	@api.depends(
		'product_uom_line_id.list_price',
		'unit_of_measure_id'
	)
	def _compute_list_price(self):
		for rec in self:
			product = rec.product_uom_line_id
			target_uom = rec.unit_of_measure_id
			base_uom = product.uom_id if product else False

			if product and base_uom and target_uom:
				# v19: uom.uom.factor_inv removed; `factor` is the absolute
				# quantity in reference units (== v18 factor_inv).
				# Step 1: price per reference UOM (Piece)
				price_per_ref = product.list_price / base_uom.factor

				# Step 2: price for selected UOM
				rec.sale_price = price_per_ref * target_uom.factor
			else:
				rec.sale_price = 0.0

	# v19: load this model through pos.load.mixin so the frontend receives the
	# records via .read(fields, load=False). Using search_read() (load='_classic_read')
	# returned many2one fields as [id, name] pairs, which broke relational linking
	# in the POS models and made the Change-UOM popup always empty.
	@api.model
	def _load_pos_data_domain(self, data, config):
		return []

	@api.model
	def _load_pos_data_fields(self, config):
		return [
			"id",
			"product_uom_line_id",
			"unit_of_measure_id",
			"sale_price",
		]



class POSSession(models.Model):
	_inherit = 'pos.session'

	# v19: the product fields (product_uom_ids / point_of_sale_uom) are added in
	# ProductProduct._load_pos_data_fields above. The legacy v16/17
	# `_loader_params_product_product` hook no longer exists in v19 and has been
	# removed. We only register the extra model to load here.
	@api.model
	def _load_pos_data_models(self, config):
		data = super()._load_pos_data_models(config)
		data += ['product.template.uom.line']
		return data

# NOTE: Odoo 19 removed the `uom.category` model (UoM is now a flat
# `uom.uom` tree linked through `relative_uom_id`/`relative_factor`). The
# `auto_calculate_sale_price` flag that lived on the category therefore has no
# target model in v19 and its extension has been removed. See
# `_onchange_point_of_sale_uom` above for the functional impact.

class PosPicking(models.Model):
	_inherit = 'stock.picking'

	def _create_move_from_pos_order_lines(self, lines):
		self.ensure_one()
		def get_grouping_key(line):
			return (line.product_id.id, line.second_uom_id.id, tuple(sorted(line.attribute_value_ids.ids)), line.second_uom_id.id)

		lines_by_product_and_attrs = groupby(sorted(lines, key=get_grouping_key), key=get_grouping_key)
		move_vals = []
		for dummy, olines in lines_by_product_and_attrs:
			order_lines = self.env['pos.order.line'].concat(*olines)
			move_vals.append(self._prepare_stock_move_vals(order_lines[0], order_lines))
		moves = self.env['stock.move'].create(move_vals)
		confirmed_moves = moves._action_confirm()
		confirmed_moves._add_mls_related_to_order(lines, are_qties_done=True)
		confirmed_moves.picked = True
		self._link_owner_on_return_picking(lines)

	def _prepare_stock_move_vals(self, first_line, order_lines):
		# v19: `stock.move` no longer has a `name` field (passing it raises
		# ValueError: Invalid field 'name' in 'stock.move'). The core vals are
		# already correct for v19 and express `product_uom_qty` in the POS line
		# UOM. We inherit them and, when a multi-UOM (second) unit was selected
		# on the line, express the move in that UOM so inventory is deducted
		# using the configured conversion ratio instead of the base unit.
		# Lines are grouped by `second_uom_id` in _create_move_from_pos_order_lines,
		# so `first_line.second_uom_id` represents the whole group.
		vals = super()._prepare_stock_move_vals(first_line, order_lines)
		if first_line.second_uom_id:
			vals['product_uom'] = first_line.second_uom_id.id
		return vals


class StockMove(models.Model):
	_inherit = 'stock.move'

	def _add_mls_related_to_order(self, related_order_lines, are_qties_done=True):
		lines_data = self._prepare_lines_data_dict(related_order_lines)
		# Moves with product_id not in related_order_lines. This can happend e.g. when product_id has a phantom-type bom.
		moves_to_assign = self.filtered(lambda m: m.product_id.id not in lines_data or m.product_id.tracking == 'none'
												  or (not m.picking_type_id.use_existing_lots and not m.picking_type_id.use_create_lots))

		# Check for any conversion issues in the moves before setting quantities
		uoms_with_issues = set()
		
		for move in moves_to_assign.filtered(lambda m: m.product_uom_qty and m.product_uom != m.product_id.uom_id):
			converted_qty = move.product_uom._compute_quantity(
				move.product_uom_qty,
				move.product_id.uom_id,
				rounding_method='HALF-UP'
			)
			if not converted_qty:
				uoms_with_issues.add(
					(move.product_uom.name, move.product_id.uom_id.name)
				)

		if uoms_with_issues:
			error_message_lines = [
				_("Conversion Error: The following unit of measure conversions result in a zero quantity due to rounding:")
			]
			for uom_from, uom_to in uoms_with_issues:
				error_message_lines.append(_(' - From "%(uom_from)s" to "%(uom_to)s"', uom_from=uom_from, uom_to=uom_to))
			error_message_lines.append(
				_("\nThis issue occurs because the quantity becomes zero after rounding during the conversion. "
				"To fix this, adjust the conversion factors or rounding method to ensure that even the smallest quantity in the original unit "
				"does not round down to zero in the target unit.")
			)

			raise UserError('\n'.join(error_message_lines))

		for move in moves_to_assign:
			move.quantity = move.product_uom_qty
		moves_remaining = self - moves_to_assign
		existing_lots = moves_remaining._create_production_lots_for_pos_order(related_order_lines)
		move_lines_to_create = []
		mls_qties = []
		if are_qties_done:
			for move in moves_remaining:
				move.move_line_ids.unlink()
				for line in lines_data[move.product_id.id]['order_lines']:
					if line.product_id.id == move.product_id.id and line.second_uom_id.id == move.product_uom.id:
						sum_of_lots = 0

						for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
							uom_search = self.env['uom.uom'].sudo().search([('id', '=', line.custom_uom_number_id)])
							baseuom = line.product_id.uom_id
							total_qty = 0
							if baseuom != uom_search:
								total_qty += line.qty / (baseuom.factor / uom_search.factor)  # v19: factor (== v18 factor_inv) converts to base UOM
							else:
								total_qty += line.qty
							qty = 1 if line.product_id.tracking == 'serial' else abs(total_qty)
							ml_vals = dict(move._prepare_move_line_vals(qty))
							if existing_lots:
								existing_lot = existing_lots.filtered_domain([('product_id', '=', line.product_id.id), ('name', '=', lot.lot_name)])
								quant = self.env['stock.quant']
								if existing_lot:
									quant = self.env['stock.quant'].search(
										[('lot_id', '=', existing_lot.id), ('quantity', '>', '0.0'), ('location_id', 'child_of', move.location_id.id)],
										order='id desc',
										limit=1
									)
									if quant:
										ml_vals.update({
											'quant_id': quant.id,
										})
									else:
										ml_vals.update({
											'lot_name': existing_lot.name,
											'lot_id': existing_lot.id,
										})
							else:
								ml_vals.update({'lot_name': lot.lot_name})
							move_lines_to_create.append(ml_vals)
							mls_qties.append(qty)
							sum_of_lots += qty

			self.env['stock.move.line'].create(move_lines_to_create)
		else:
			for move in moves_remaining:
				for line in lines_data[move.product_id.id]['order_lines']:
					if line.product_id.id == move.product_id.id and line.second_uom_id.id == move.product_uom.id:
						for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
							uom_search = self.env['uom.uom'].sudo().search([('id', '=', line.custom_uom_number_id)])
							baseuom = line.product_id.uom_id
							total_qty = 0
							if baseuom != uom_search:
								total_qty += line.qty / (baseuom.factor / uom_search.factor)  # v19: factor (== v18 factor_inv) converts to base UOM
							else:
								total_qty += line.qty
							qty = 1 if line.product_id.tracking == 'serial' else abs(total_qty)
							if existing_lots:
								existing_lot = existing_lots.filtered_domain([('product_id', '=', line.product_id.id), ('name', '=', lot.lot_name)])
								if existing_lot:
									move._update_reserved_quantity(qty, move.location_id, lot_id=existing_lot)
									continue

