# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, fields, models, _
from odoo.tools import float_is_zero, SQL
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosConfiguration(models.Model):
	_inherit = 'pos.config'

	discount_type = fields.Selection(
		[('percentage', "Percentage"), ('fixed', "Fixed")],
		string='Discount Type',
		default='percentage',
		help='Seller can apply different Discount Type in POS.',
	)


class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	discount_type = fields.Selection(related='pos_config_id.discount_type', readonly=False)


class PosOrderLine(models.Model):
	_inherit = 'pos.order.line'

	discount_line_type = fields.Char(string='Discount Type', readonly=True)
	discount_type = fields.Char(string='Discount Type Label', readonly=True)

	def _compute_amount_line_all(self):
		for line in self:
			fpos = line.order_id.fiscal_position_id
			tax_ids_after_fiscal_position = (
				fpos.map_tax(line.tax_ids, line.product_id, line.order_id.partner_id)
				if fpos else line.tax_ids
			)
			if line.discount_line_type in ["Fixed", 'fixed']:
				price = line.price_unit - line.discount
			else:
				price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
			taxes = tax_ids_after_fiscal_position.compute_all(
				price,
				line.order_id.pricelist_id.currency_id,
				line.qty,
				product=line.product_id,
				partner=line.order_id.partner_id,
			)
			line.update({
				'price_subtotal_incl': taxes['total_included'],
				'price_subtotal': taxes['total_excluded'],
			})


class PosOrder(models.Model):
	_inherit = 'pos.order'

	discount_type = fields.Char(string='Discount Type', readonly=True)

	def _prepare_invoice_vals(self):
		res = super()._prepare_invoice_vals()
		res.update({'pos_order_id': self.id})
		return res

	def _get_invoice_lines_values(self, line_values, pos_line, move_type):
		res = super()._get_invoice_lines_values(line_values, pos_line, move_type)
		res.update({
			'pos_order_line_id': pos_line.id,
			'pos_order_id': self.id,
			'discount_line_type': pos_line.discount_line_type,
		})
		return res

	@api.model
	def _amount_line_tax(self, line, fiscal_position_id):
		taxes = line.tax_ids.filtered(lambda t: t.company_id.id == line.order_id.company_id.id)
		taxes = fiscal_position_id.map_tax(taxes)
		if line.discount_line_type == 'Percentage':
			price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
		else:
			price = line.price_unit - line.discount
		taxes = taxes.compute_all(
			price,
			line.order_id.pricelist_id.currency_id,
			line.qty,
			product=line.product_id,
			partner=line.order_id.partner_id or False,
		)['taxes']
		return sum(tax.get('amount', 0.0) for tax in taxes)

	@api.model
	def _process_order(self, order, existing_order):
		"""
		Delegate entirely to super() so we stay compatible with whatever
		combo-linking API this Odoo 19 build uses (_prepare_combo_line_uuids,
		_link_combo_items, or anything else), then apply our discount logic
		on the saved record.
		"""
		pos_order_id = super()._process_order(order, existing_order)

		# super() returns the integer id of the saved order
		pos_order = self.env['pos.order'].browse(pos_order_id) if isinstance(pos_order_id, int) else pos_order_id

		if not pos_order:
			return pos_order_id

		discount_type_raw = order.get('discount_type')
		if discount_type_raw:
			if discount_type_raw == 'percentage':
				pos_order.sudo().write({'discount_type': 'Percentage'})
				pos_order.lines.sudo().write({'discount_line_type': 'Percentage'})
			elif discount_type_raw == 'fixed':
				pos_order.sudo().write({'discount_type': 'Fixed'})
				pos_order.lines.sudo().write({'discount_line_type': 'Fixed'})
		else:
			config_discount = pos_order.config_id.discount_type
			if config_discount == 'percentage':
				pos_order.sudo().write({'discount_type': 'Percentage'})
				pos_order.lines.sudo().write({'discount_line_type': 'Percentage'})
			elif config_discount == 'fixed':
				pos_order.sudo().write({'discount_type': 'Fixed'})
				pos_order.lines.sudo().write({'discount_line_type': 'Fixed'})

		return pos_order_id


class ReportSaleDetailsInherit(models.AbstractModel):
	_inherit = 'report.point_of_sale.report_saledetails'

	def _get_products_and_taxes_dict(self, line, products, taxes, currency):
		key2 = (line.product_id, line.price_unit, line.discount, line.discount_line_type)
		key1 = (
			line.product_id.product_tmpl_id.pos_categ_ids[0].name
			if len(line.product_id.product_tmpl_id.pos_categ_ids)
			else _('Not Categorized')
		)
		products.setdefault(key1, {})
		products[key1].setdefault(key2, [0.0, 0.0, 0.0])
		products[key1][key2][0] += line.qty
		products[key1][key2][1] += line.currency_id.round(
			line.price_unit * line.qty * (100 - line.discount) / 100.0
		)
		products[key1][key2][2] += line.price_subtotal

		if line.tax_ids_after_fiscal_position:
			line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(
				line.price_unit * (1 - (line.discount or 0.0) / 100.0),
				currency,
				line.qty,
				product=line.product_id,
				partner=line.order_id.partner_id or False,
			)
			base_amounts = {}
			for tax in line_taxes['taxes']:
				taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount': 0.0, 'base_amount': 0.0})
				taxes[tax['id']]['tax_amount'] += tax['amount']
				base_amounts[tax['id']] = tax['base']
			for tax_id, base_amount in base_amounts.items():
				taxes[tax_id]['base_amount'] += base_amount
		else:
			taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount': 0.0, 'base_amount': 0.0})
			taxes[0]['base_amount'] += line.price_subtotal_incl

		return products, taxes

	@api.model
	def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
		if not session_ids:
			date_start, date_stop = self._get_date_start_and_date_stop(date_start, date_stop)

		domain = self._get_domain(date_start, date_stop, config_ids, session_ids, **kwargs)
		orders = self.env['pos.order'].search(domain)

		if config_ids:
			config_currencies = self.env['pos.config'].search([('id', 'in', config_ids)]).mapped('currency_id')
		else:
			config_currencies = self.env['pos.session'].search([('id', 'in', session_ids)]).mapped('config_id.currency_id')

		if config_currencies and all(i == config_currencies.ids[0] for i in config_currencies.ids):
			user_currency = config_currencies[0]
		else:
			user_currency = self.env.company.currency_id

		total = 0.0
		products_sold = {}
		taxes = {'base_amount': 0.0, 'taxes': {}}
		refund_done = {}
		refund_taxes = {'base_amount': 0.0, 'taxes': {}}

		for order in orders:
			if user_currency != order.pricelist_id.currency_id:
				total += order.pricelist_id.currency_id._convert(
					order.amount_total, user_currency, order.company_id,
					order.date_order or fields.Date.today(),
				)
			else:
				total += order.amount_total
			currency = order.session_id.currency_id

			for line in order.lines:
				if line.qty >= 0:
					products_sold, taxes = self._get_products_and_taxes_dict(line, products_sold, taxes, currency)
				else:
					refund_done, refund_taxes = self._get_products_and_taxes_dict(line, refund_done, refund_taxes, currency)

		taxes_info = self._get_taxes_info(taxes)
		refund_taxes_info = self._get_taxes_info(refund_taxes)
		taxes = taxes['taxes']
		refund_taxes = refund_taxes['taxes']

		payment_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
		if payment_ids:
			method_name = self.env['pos.payment.method']._field_to_sql('method', 'name')
			self.env.cr.execute(SQL("""
				SELECT method.id as id, payment.session_id as session, %(method_name)s as name,
				       method.is_cash_count as cash, sum(amount) total, method.journal_id journal_id
				FROM pos_payment AS payment, pos_payment_method AS method
				WHERE payment.payment_method_id = method.id
				  AND payment.id IN %(payment_ids)s
				GROUP BY method.name, method.is_cash_count, payment.session_id, method.id, journal_id
			""", method_name=method_name, payment_ids=tuple(payment_ids)))
			payments = self.env.cr.dictfetchall()
		else:
			payments = []

		configs = []
		sessions = []
		if config_ids:
			configs = self.env['pos.config'].search([('id', 'in', config_ids)])
			if session_ids:
				sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
			else:
				sessions = self.env['pos.session'].search([
					('config_id', 'in', configs.ids),
					('start_at', '>=', date_start),
					('stop_at', '<=', date_stop),
				])
		else:
			sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
			for session in sessions:
				configs.append(session.config_id)

		for payment in payments:
			payment['count'] = False

		for session in sessions:
			cash_counted = session.cash_register_balance_end_real or 0
			is_cash_method = False
			for payment in payments:
				account_payments = self.env['account.payment'].search([('pos_session_id', '=', session.id)])
				if payment['session'] == session.id:
					if not payment['cash']:
						ref_value = "Closing difference in %s (%s)" % (payment['name'], session.name)
						account_move = self.env['account.move'].search([("ref", "=", ref_value)], limit=1)
						if account_move:
							payment_method = self.env['pos.payment.method'].browse(payment['id'])
							is_loss = any(l.account_id == payment_method.journal_id.loss_account_id for l in account_move.line_ids)
							is_profit = any(l.account_id == payment_method.journal_id.profit_account_id for l in account_move.line_ids)
							payment['final_count'] = payment['total']
							payment['money_difference'] = -account_move.amount_total if is_loss else account_move.amount_total
							payment['money_counted'] = payment['final_count'] + payment['money_difference']
							payment['cash_moves'] = []
							if is_profit:
								payment['cash_moves'] = [{'name': 'Difference observed during the counting (Profit)', 'amount': payment['money_difference']}]
							elif is_loss:
								payment['cash_moves'] = [{'name': 'Difference observed during the counting (Loss)', 'amount': payment['money_difference']}]
							payment['count'] = True
						elif payment['id'] in account_payments.mapped('pos_payment_method_id.id'):
							account_payment = account_payments.filtered(lambda p: p.pos_payment_method_id.id == payment['id'])
							payment['final_count'] = payment['total']
							payment['money_counted'] = sum(account_payment.mapped('amount'))
							payment['money_difference'] = payment['money_counted'] - payment['final_count']
							payment['cash_moves'] = []
							if payment['money_difference'] > 0:
								payment['cash_moves'] = [{'name': 'Difference observed during the counting (Profit)', 'amount': payment['money_difference']}]
							elif payment['money_difference'] < 0:
								payment['cash_moves'] = [{'name': 'Difference observed during the counting (Loss)', 'amount': payment['money_difference']}]
							payment['count'] = True
					else:
						is_cash_method = True
						previous_session = self.env['pos.session'].search([
							('id', '<', session.id), ('state', '=', 'closed'),
							('config_id', '=', session.config_id.id),
						], limit=1)
						payment['final_count'] = payment['total'] + previous_session.cash_register_balance_end_real + session.cash_real_transaction
						payment['money_counted'] = cash_counted
						payment['money_difference'] = payment['money_counted'] - payment['final_count']
						cash_moves = self.env['account.bank.statement.line'].search([('pos_session_id', '=', session.id)])
						cash_in_out_list = []
						cash_in_count = cash_out_count = 0
						if session.cash_register_balance_start > 0:
							cash_in_out_list.append({'name': _('Cash Opening'), 'amount': session.cash_register_balance_start})
						for cash_move in cash_moves:
							if cash_move.amount > 0:
								cash_in_count += 1
								name = f'Cash in {cash_in_count}'
							else:
								cash_out_count += 1
								name = f'Cash out {cash_out_count}'
							if cash_move.move_id.journal_id.id == payment['journal_id']:
								cash_in_out_list.append({'name': cash_move.payment_ref or name, 'amount': cash_move.amount})
						payment['cash_moves'] = cash_in_out_list
						payment['count'] = True

			if not is_cash_method:
				cash_name = _('Cash %(session_name)s', session_name=session.name)
				previous_session = self.env['pos.session'].search([
					('id', '<', session.id), ('state', '=', 'closed'),
					('config_id', '=', session.config_id.id),
				], limit=1)
				final_count = previous_session.cash_register_balance_end_real + session.cash_real_transaction
				cash_difference = session.cash_register_balance_end_real - final_count
				cash_moves = self.env['account.bank.statement.line'].search([('pos_session_id', '=', session.id)], order='date asc')
				cash_in_out_list = []
				if previous_session.cash_register_balance_end_real > 0:
					cash_in_out_list.append({'name': _('Cash Opening'), 'amount': previous_session.cash_register_balance_end_real})
				if cash_difference != 0:
					cash_moves = cash_moves[:-1]
				for cash_move in cash_moves:
					cash_in_out_list.append({'name': cash_move.payment_ref, 'amount': cash_move.amount})
				payments.insert(0, {
					'name': cash_name, 'total': 0, 'final_count': final_count,
					'money_counted': session.cash_register_balance_end_real,
					'money_difference': cash_difference, 'cash_moves': cash_in_out_list,
					'count': True, 'session': session.id,
				})

		products = []
		refund_products = []
		for category_name, product_list in products_sold.items():
			products.append({
				'name': category_name,
				'products': sorted([{
					'product_id': product.id, 'product_name': product.name,
					'code': product.default_code, 'quantity': qty,
					'price_unit': price_unit, 'discount': discount,
					'uom': product.uom_id.name, 'total_paid': product_total,
					'base_amount': base_amount, 'discount_line_type': discount_line_type,
				} for (product, price_unit, discount, discount_line_type), (qty, product_total, base_amount) in product_list.items()],
				key=lambda l: l['product_name']),
			})
		products = sorted(products, key=lambda l: str(l['name']))

		for category_name, product_list in refund_done.items():
			refund_products.append({
				'name': category_name,
				'products': sorted([{
					'product_id': product.id, 'product_name': product.name,
					'code': product.default_code, 'quantity': qty,
					'price_unit': price_unit, 'discount': discount,
					'uom': product.uom_id.name, 'total_paid': product_total,
					'base_amount': base_amount, 'discount_line_type': discount_line_type,
				} for (product, price_unit, discount, discount_line_type), (qty, product_total, base_amount) in product_list.items()],
				key=lambda l: l['product_name']),
			})
		refund_products = sorted(refund_products, key=lambda l: str(l['name']))

		products, products_info = self._get_total_and_qty_per_category(products)
		refund_products, refund_info = self._get_total_and_qty_per_category(refund_products)

		currency = {
			'symbol': user_currency.symbol,
			'position': user_currency.position == 'after',
			'total_paid': user_currency.round(total),
			'precision': user_currency.decimal_places,
		}

		session_name = False
		if len(sessions) == 1:
			state = sessions[0].state
			date_start = sessions[0].start_at
			date_stop = sessions[0].stop_at
			session_name = sessions[0].name
		else:
			state = "multiple"

		config_names = [config.name for config in configs]

		discount_number = len(orders.filtered(lambda o: o.lines.filtered(lambda l: l.discount > 0)))
		discount_amount = sum(l._get_discount_amount() for l in orders.lines.filtered(lambda l: l.discount > 0))

		invoiceList = []
		invoiceTotal = 0
		for session in sessions:
			invoiceList.append({'name': session.name, 'invoices': session._get_invoice_total_list()})
			invoiceTotal += session._get_total_invoice()

		for payment in payments:
			if payment.get('id'):
				payment['name'] = (
					self.env['pos.payment.method'].browse(payment['id']).name
					+ ' '
					+ self.env['pos.session'].browse(payment['session']).name
				)

		return {
			'opening_note': sessions[0].opening_notes if len(sessions) == 1 else False,
			'closing_note': sessions[0].closing_notes if len(sessions) == 1 else False,
			'state': state, 'currency': currency,
			'nbr_orders': len(orders), 'date_start': date_start, 'date_stop': date_stop,
			'session_name': session_name or False, 'config_names': config_names,
			'payments': payments, 'company_name': self.env.company.name,
			'taxes': list(taxes.values()), 'taxes_info': taxes_info,
			'products': products, 'products_info': products_info,
			'refund_taxes': list(refund_taxes.values()), 'refund_taxes_info': refund_taxes_info,
			'refund_info': refund_info, 'refund_products': refund_products,
			'discount_number': discount_number, 'discount_amount': discount_amount,
			'invoiceList': invoiceList, 'invoiceTotal': invoiceTotal,
		}
