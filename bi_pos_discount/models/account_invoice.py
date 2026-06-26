# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from functools import partial
from odoo.tools import frozendict, formatLang, format_date, float_is_zero
import psycopg2
import pytz
from odoo.tools.misc import formatLang
from odoo import api, fields, models, tools, _, Command
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo.http import request
from functools import partial


class AccountInvoiceInherit(models.Model):
	_inherit = "account.move"

	pos_order_id = fields.Many2one('pos.order', string="POS order")
	discount_amt = fields.Float('Discount Final Amount')
	discount_amount = fields.Float('Discount Amount')
	discount_amount_line = fields.Monetary(string="Discount Line")
	config_inv_tax = fields.Monetary(string="total disc tax",compute="_calculate_discount",store=True)

	def _calculate_discount(self):
		res=0.0
		for move in self:
			for line in move.invoice_line_ids:
				if line.discount_line_type == 'Fixed':
					res += line.discount
				elif line.discount_line_type == 'Percentage':
					res += line.price_subtotal * (line.discount/ 100)
		return res


	@api.depends(
		'line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched',
		'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
		'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
		'line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_matched',
		'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
		'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
		'line_ids.balance',
		'line_ids.currency_id',
		'line_ids.amount_currency',
		'line_ids.amount_residual',
		'line_ids.amount_residual_currency',
		'line_ids.payment_id.state',
		'line_ids.full_reconcile_id','line_ids.discount_line_type','line_ids.discount','state')
	def _compute_amount(self):
		for move in self:
			total_untaxed, total_untaxed_currency = 0.0, 0.0
			total_tax, total_tax_currency = 0.0, 0.0
			total_residual, total_residual_currency = 0.0, 0.0
			total, total_currency = 0.0, 0.0

			for line in move.line_ids:
				if move.is_invoice(True):
					# === Invoices ===
					if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
						# Tax amount.
						total_tax += line.balance
						total_tax_currency += line.amount_currency
						total += line.balance
						total_currency += line.amount_currency
					elif line.display_type in ('product', 'rounding'):
						# Untaxed amount.
						total_untaxed += line.balance
						total_untaxed_currency += line.amount_currency
						total += line.balance
						total_currency += line.amount_currency
					elif line.display_type == 'payment_term':
						# Residual amount.
						total_residual += line.amount_residual
						total_residual_currency += line.amount_residual_currency
				else:
					# === Miscellaneous journal entry ===
					if line.debit:
						total += line.balance
						total_currency += line.amount_currency
			sign = move.direction_sign
			move.amount_untaxed = sign * total_untaxed_currency
			move.amount_tax = sign * total_tax_currency
			move.amount_total = sign * total_currency
			move.amount_residual = -sign * total_residual_currency
			move.amount_untaxed_signed = -total_untaxed
			move.amount_untaxed_in_currency_signed = -total_untaxed_currency
			move.amount_tax_signed = -total_tax
			move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
			move.amount_residual_signed = total_residual
			move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)
			res = move._calculate_discount()
			move.discount_amt = res



class AccountTax(models.Model):
	_inherit = "account.tax"

	@api.model
	def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
		price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
		if base_line['record']:
			if base_line['record']._name in ['account.move.line','sale.order.line']:
				if base_line['record'].discount_line_type in ['fixed','Fixed']:
					price_unit_after_discount = base_line['price_unit']- base_line['discount']
				if base_line['record'].discount_line_type in ['percentage','Percentage']:
					price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
			else:

				price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
		else:
			price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
		
		taxes_computation = base_line['tax_ids']._get_tax_details(
			price_unit=price_unit_after_discount,
			quantity=base_line['quantity'],
			precision_rounding=base_line['currency_id'].rounding,
			rounding_method=rounding_method or company.tax_calculation_rounding_method,
			product=base_line['product_id'],
			special_mode=base_line['special_mode'],
		)
		rate = base_line['rate']
		tax_details = base_line['tax_details'] = {
			'raw_total_excluded_currency': taxes_computation['total_excluded'],
			'raw_total_excluded': taxes_computation['total_excluded'] / rate if rate else 0.0,
			'raw_total_included_currency': taxes_computation['total_included'],
			'raw_total_included': taxes_computation['total_included'] / rate if rate else 0.0,
			'taxes_data': [],
		}
		if company.tax_calculation_rounding_method == 'round_per_line':
			tax_details['raw_total_excluded'] = company.currency_id.round(tax_details['raw_total_excluded'])
			tax_details['raw_total_included'] = company.currency_id.round(tax_details['raw_total_included'])
		for tax_data in taxes_computation['taxes_data']:
			tax_amount = tax_data['tax_amount'] / rate if rate else 0.0
			base_amount = tax_data['base_amount'] / rate if rate else 0.0
			if company.tax_calculation_rounding_method == 'round_per_line':
				tax_amount = company.currency_id.round(tax_amount)
				base_amount = company.currency_id.round(base_amount)
			tax_details['taxes_data'].append({
				**tax_data,
				'raw_tax_amount_currency': tax_data['tax_amount'],
				'raw_tax_amount': tax_amount,
				'raw_base_amount_currency': tax_data['base_amount'],
				'raw_base_amount': base_amount,
			})


class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"
	discount_line_type = fields.Char(string='Discount Type',
									 readonly=True, store=True)

class AccountInvoiceLineInherit(models.Model):
	_inherit = "account.move.line"

	pos_order_id = fields.Many2one('pos.order', string="POS order")
	pos_order_line_id = fields.Many2one('pos.order.line', string="POS order Line")
	discount_line_type = fields.Char(string='Discount Type',
									 readonly=True, store=True)
	discount_amt = fields.Float('Discount Final Amount')
	discount_amount = fields.Float('Discount Amount')


	@api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
	def _compute_totals(self):
		for line in self:
			if line.display_type != 'product':
				line.price_total = line.price_subtotal = False
			if line.discount_line_type and line.discount_line_type in ["Fixed","fixed"]:

				line_discount_price_unit = line.price_unit - line.discount
			else:

				line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
			subtotal = line.quantity * line_discount_price_unit
			if line.tax_ids:
				taxes_res = line.tax_ids.compute_all(
					line_discount_price_unit,
					quantity=line.quantity,
					currency=line.currency_id,
					product=line.product_id,
					partner=line.partner_id,
					is_refund=line.is_refund)
				line.price_subtotal = taxes_res['total_excluded']
				line.price_total = taxes_res['total_included']
			else:
				line.price_total = line.price_subtotal = subtotal
				

	
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:   