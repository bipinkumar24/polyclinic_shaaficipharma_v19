# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PharmacyAuditLog(models.Model):
    _name = 'pharmacy.audit.log'
    _description = 'Pharmacy Audit Trail Entry'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Description', required=True)
    log_date = fields.Datetime(
        string='Date/Time', default=fields.Datetime.now, required=True)
    user_id = fields.Many2one(
        'res.users', string='User', default=lambda self: self.env.user,
        required=True)
    action_type = fields.Selection(
        selection=[
            ('product_edit', 'Product Edit'),
            ('price_change', 'Price Change'),
            ('inventory_adjust', 'Inventory Adjustment'),
            ('pos_override', 'POS Override'),
            ('discount', 'Discount Applied'),
            ('refund', 'Refund / Void'),
            ('other', 'Other'),
        ],
        string='Action Type', required=True, default='other')
    model_name = fields.Char(string='Model')
    res_id = fields.Integer(string='Record ID')
    branch_id = fields.Many2one('pharmacy.branch', string='Branch')
    old_value = fields.Char(string='Old Value')
    new_value = fields.Char(string='New Value')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    note = fields.Text(string='Details')

    @api.model
    def log_action(self, action_type, name, **kwargs):
        """Helper to create an audit entry from anywhere in the codebase."""
        vals = {'action_type': action_type, 'name': name}
        vals.update({k: v for k, v in kwargs.items() if k in self._fields})
        return self.sudo().create(vals)
