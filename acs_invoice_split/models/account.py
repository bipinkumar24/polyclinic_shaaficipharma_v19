# -*- coding: utf-8 -*-

from odoo import api,fields,models,_
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    qty_to_split = fields.Float(string='Split Qty')
    price_to_split = fields.Float(string='Split Price')
    full_cover = fields.Boolean(string='Full Cover (100% on other party)')
    copied_line_id = fields.Many2one('account.move.line', 'Copied Invoice Line')

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default)
        for rec, vals in zip(self, vals_list):
            vals['copied_line_id'] = rec.id
        return vals_list
    
    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountMoveLine, self).create(vals_list)
        for line in res:
            installed_sale_management = self.env['ir.module.module'].sudo().search([('name','=','sale_management'),('state','=','installed')])
            if installed_sale_management and line.copied_line_id:
                sale_lines = self.env['sale.order.line'].search([('invoice_lines','in',line.copied_line_id.id)])
                for order_line in sale_lines:
                    order_line.with_context(check_move_validity=False).invoice_lines = [(4,line.id)]
        return res
