# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
#
# Odoo 19 migration note
# ----------------------
# The base wizard ``stock.valuation.layer.revaluation`` (and its form view) were
# removed together with ``stock.valuation.layer``. To preserve the warehouse-wise
# revaluation feature we provide a standalone wizard that:
#   * adjusts the warehouse cost bucket (sh.warehouse.cost),
#   * adjusts the global standard price proportionally (Odoo records the change in
#     ``product.value`` automatically),
#   * for real-time valued products, posts the matching accounting entry.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WarehouseRevaluation(models.TransientModel):
    _name = 'sh.warehouse.revaluation'
    _description = 'Warehouse Wise Stock Revaluation'

    product_id = fields.Many2one(
        'product.product', string="Product", required=True,
        domain=[('is_storable', '=', True)])
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", required=True)
    company_id = fields.Many2one(
        'res.company', string="Company",
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')

    added_value = fields.Monetary("Added Value", currency_field='currency_id', required=True)
    current_cost = fields.Float(
        string="Current Warehouse Cost", compute='_compute_current', readonly=True)
    current_quantity = fields.Float(
        string="Quantity On Hand (Warehouse)", compute='_compute_current', readonly=True)

    reason = fields.Char("Reason")
    account_journal_id = fields.Many2one('account.journal', "Journal")
    account_id = fields.Many2one('account.account', "Counterpart Account")
    date = fields.Date("Accounting Date", default=fields.Date.context_today)

    @api.depends('product_id', 'warehouse_id', 'company_id')
    def _compute_current(self):
        for rec in self:
            rec.current_cost = 0.0
            rec.current_quantity = 0.0
            if rec.product_id and rec.warehouse_id:
                product = rec.product_id.with_company(rec.company_id)
                line = product.warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id == rec.warehouse_id)[:1]
                rec.current_cost = line.cost
                rec.current_quantity = product.with_context(
                    warehouse_id=rec.warehouse_id.id).qty_available

    def action_validate_revaluation(self):
        """Revaluate the stock of ``self.product_id`` in ``self.warehouse_id``."""
        self.ensure_one()
        if self.currency_id.is_zero(self.added_value):
            raise UserError(_("The added value doesn't have any impact on the stock valuation"))

        product = self.product_id.with_company(self.company_id)
        if product.cost_method != 'average':
            raise UserError(_("Warehouse-wise revaluation is only available for Average Cost (AVCO) products."))

        line = product.warehouse_cost_lines.filtered(
            lambda x: x.warehouse_id == self.warehouse_id)[:1]
        if not line:
            raise UserError(_("Selected Warehouse has no stock for this Product"))

        qty = self.current_quantity
        if qty <= 0:
            raise UserError(_("There is no on-hand quantity to revalue in this warehouse."))

        # 1. Update the warehouse cost bucket.
        line.cost += self.added_value / qty

        # 2. Update the global standard price proportionally. Odoo records the
        #    change in ``product.value`` (and posts accounting) on its own.
        global_qty = product.with_context(warehouse_id=False).qty_available
        if global_qty:
            product.with_context(disable_auto_revaluation=True).standard_price += self.added_value / global_qty

        # 3. For real-time valued products, post the warehouse revaluation amount.
        if product.valuation != 'real_time':
            return True

        accounts = product.product_tmpl_id.get_product_accounts()
        valuation_account = accounts.get('stock_valuation')
        if not valuation_account or not self.account_id:
            raise UserError(_("Please set a counterpart account to post the revaluation entry."))

        if self.added_value < 0:
            debit_account_id = self.account_id.id
            credit_account_id = valuation_account.id
        else:
            debit_account_id = valuation_account.id
            credit_account_id = self.account_id.id

        move_vals = {
            'journal_id': self.account_journal_id.id or accounts['stock_journal'].id,
            'company_id': self.company_id.id,
            'ref': _("Revaluation of %s", product.display_name),
            'date': self.date or fields.Date.today(),
            'move_type': 'entry',
            'line_ids': [(0, 0, {
                'name': self.reason or _("Warehouse Revaluation"),
                'account_id': debit_account_id,
                'debit': abs(self.added_value),
                'credit': 0,
                'product_id': product.id,
            }), (0, 0, {
                'name': self.reason or _("Warehouse Revaluation"),
                'account_id': credit_account_id,
                'debit': 0,
                'credit': abs(self.added_value),
                'product_id': product.id,
            })],
        }
        account_move = self.env['account.move'].create(move_vals)
        account_move._post()
        return True
