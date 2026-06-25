# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    internal_journal_entries_ids = fields.Many2many("account.move", string="Journal Entry ", copy=False)

    def action_view_journal_entry(self):
        self.ensure_one()
        return {
            "name": _("Journal Entries"),
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "account.move",
            "domain": [('id', 'in', self.internal_journal_entries_ids.ids)],
        }

    def _action_done(self):
        res = super()._action_done()
        if self.picking_type_code == "internal":
            self.journal_entry_internal_transfer()
        return res

    def action_create_internal_transfer_journal_entry(self):
        for picking in self:
            source_location = picking.location_id
            dest_location = picking.location_dest_id

            source_branch = source_location.warehouse_id.branch_id
            dest_branch = dest_location.warehouse_id.branch_id

            move_lines = picking.move_line_ids.filtered(lambda m: m.product_id.valuation == 'real_time')
            
            if not move_lines:
                continue

            journals = move_lines.mapped('product_id.categ_id.property_stock_journal')
            if len(journals) > 1:
                raise UserError("Multiple Stock journals found.")
            elif not journals:
                raise UserError("Stock journal not found.")
            stock_journal = journals[0]

            # First move (source side - CREDIT)
            first_move_vals = {
                'ref': picking.name,
                'journal_id': stock_journal.id,
                'date': fields.Date.context_today(picking),
                'branch_id': source_branch.id,
                'location_id': source_location.id,  # <-- Added
                'line_ids': [],
            }

            # Second move (destination side - DEBIT)
            second_move_vals = {
                'ref': picking.name,
                'journal_id': stock_journal.id,
                'date': fields.Date.context_today(picking),
                'branch_id': dest_branch.id,
                'location_id': dest_location.id,  # <-- Added
                'line_ids': [],
            }

            for move in move_lines:
                product = move.product_id
                qty = move.quantity
                cost = product.standard_price
                amount = qty * cost

                stock_account = product.categ_id.property_stock_valuation_account_id
                inter_company_account = product.categ_id.inter_company_account

                # First entry lines (source location + branch)
                first_move_vals['line_ids'] += [
                    (0, 0, {
                        'name': f'{product.display_name} - Internal Transfer',
                        'account_id': stock_account.id,
                        'debit': 0.0,
                        'credit': amount,
                        'product_id': product.id,
                        'quantity': qty,
                        'location_id': source_location.id,
                        'branch_id': source_branch.id,
                        'product_id': product.id,
                    }),
                    (0, 0, {
                        'name': f'{product.display_name} - Internal Transfer',
                        'account_id': inter_company_account.id,
                        'debit': amount,
                        'credit': 0.0,
                        'product_id': product.id,
                        'quantity': qty,
                        'location_id': source_location.id,
                        'branch_id': False,
                        'product_id': product.id,
                    }),
                ]

                # Second entry lines (destination location + branch)
                second_move_vals['line_ids'] += [
                    (0, 0, {
                        'name': f'{product.display_name} - Internal Transfer',
                        'account_id': stock_account.id,
                        'debit': amount,
                        'credit': 0.0,
                        'product_id': product.id,
                        'quantity': qty,
                        'location_id': dest_location.id,
                        'branch_id': dest_branch.id,
                        'product_id': product.id,
                    }),
                    (0, 0, {
                        'name': f'{product.display_name} - Internal Transfer',
                        'account_id': inter_company_account.id,
                        'debit': 0.0,
                        'credit': amount,
                        'product_id': product.id,
                        'quantity': qty,
                        'location_id': dest_location.id,
                        'branch_id': False,
                        'product_id': product.id,
                    }),
                ]

            first_entry = self.env['account.move'].create(first_move_vals)
            # first_entry.line_ids.branch_id = False
            second_entry = self.env['account.move'].create(second_move_vals)
            # second_entry.line_ids.branch_id = False
            return first_entry + second_entry

    def journal_entry_internal_transfer(self):
        moves = self.action_create_internal_transfer_journal_entry()
        if moves:
            moves.action_post()
            # Remove Branch From inter_company_account
            for move in moves:
                for line in move.line_ids:
                    inter_company_account = line.product_id.categ_id.inter_company_account
                    if inter_company_account.id == line.account_id.id:
                        line.branch_id = False
            self.internal_journal_entries_ids = moves.ids
            # Link the generated journal entry to the related stock move(s).
            # In Odoo 19 the `stock.valuation.layer` model was removed; the
            # stock valuation (and its journal entry link) now lives directly on
            # `stock.move` (value / is_in / is_out / account_move_id). We keep the
            # original mapping of the old layer semantics:
            #   layer.quantity < 0  -> outgoing valued move  (move.is_out)
            #   layer.quantity > 0  -> incoming valued move  (move.is_in)
            scraps = self.env['stock.scrap'].search([('picking_id', '=', self.id)])
            stock_moves = self.move_ids + scraps.move_ids
            for stock_move in stock_moves:
                stock_account = stock_move.product_id.categ_id.property_stock_valuation_account_id
                for move in moves:
                    for line in move.line_ids:
                        if line.account_id.id == stock_account.id and line.credit > 0 and stock_move.is_out:
                            stock_move.account_move_id = move.id
                        elif line.account_id.id == stock_account.id and line.debit > 0 and stock_move.is_in:
                            stock_move.account_move_id = move.id


class StockLocation(models.Model):
    _inherit = 'stock.location'

    branch_id = fields.Many2one('res.branch', required=True)


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    branch_id = fields.Many2one('res.branch', required=True)

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    branch_id = fields.Many2one('res.branch', compute="_compute_branch_id", store=True)

    @api.depends('location_id', 'location_id.branch_id')
    def _compute_branch_id(self):
        for location in self:
            location.branch_id = location.location_id.branch_id.id

# NOTE: Odoo 19 removed the `stock.valuation.layer` model (valuation is now
# carried on `stock.move`). The previous `StockValuationLayer` extension that
# stamped a `branch_id` on each valuation layer therefore has no target model
# in v19 and has been removed to keep the registry loadable. The branch is
# still tracked on stock.location / stock.warehouse / stock.quant below.
