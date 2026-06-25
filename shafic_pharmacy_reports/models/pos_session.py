# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    branch_id = fields.Many2one(
        'pharmacy.branch', string='Branch', compute='_compute_branch_id',
        store=True)
    cash_difference = fields.Monetary(
        string='Cash Difference', compute='_compute_cash_difference',
        store=False, currency_field='currency_id')

    @api.depends('config_id')
    def _compute_branch_id(self):
        branch_model = self.env['pharmacy.branch']
        for session in self:
            branch = branch_model.search(
                [('pos_config_ids', 'in', session.config_id.id)], limit=1)
            session.branch_id = branch.id if branch else False

    @api.depends('cash_register_balance_end_real',
                 'cash_register_balance_end')
    def _compute_cash_difference(self):
        for session in self:
            session.cash_difference = (
                session.cash_register_balance_end_real -
                session.cash_register_balance_end)
