# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PharmacyBranch(models.Model):
    _name = 'pharmacy.branch'
    _description = 'Pharmacy Branch'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Branch Name', required=True, tracking=True)
    code = fields.Char(string='Branch Code', required=True, tracking=True,
                       copy=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        help='Warehouse linked to this branch for stock reporting.')
    pos_config_ids = fields.Many2many(
        'pos.config', string='POS Points',
        help='POS configurations operating at this branch.')
    manager_id = fields.Many2one('res.users', string='Branch Manager')
    pharmacist_ids = fields.Many2many(
        'res.users', 'pharmacy_branch_pharmacist_rel',
        'branch_id', 'user_id', string='Pharmacists')
    address = fields.Char(string='Address')
    phone = fields.Char(string='Phone')
    sales_target = fields.Monetary(
        string='Monthly Sales Target', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True)
    note = fields.Text(string='Notes')

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'The branch code must be unique per company.'),
    ]

    @api.constrains('warehouse_id', 'company_id')
    def _check_warehouse_company(self):
        for branch in self:
            if branch.warehouse_id and \
                    branch.warehouse_id.company_id != branch.company_id:
                raise ValidationError(_(
                    'The warehouse must belong to the same company '
                    'as the branch.'))

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for branch in self:
            branch.display_name = '[%s] %s' % (branch.code, branch.name)
