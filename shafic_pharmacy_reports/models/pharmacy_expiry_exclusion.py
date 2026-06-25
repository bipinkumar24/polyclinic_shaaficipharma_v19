# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PharmacyExpiryExclusion(models.Model):
    """Record of expired stock that should be excluded from the bonus
    rate because the loss was outside the team's control.

    Typical reasons: cold-chain equipment failure, supplier delivery of
    short-dated stock, product recall, store-wide incident. Each entry
    needs approval; only approved exclusions are deducted from the
    expired value when the scorecard is computed.

    The total is still recorded in financial reporting (expired stock
    write-off is an accounting fact) — this model only affects how the
    bonus rate is calculated.
    """
    _name = 'pharmacy.expiry.exclusion'
    _description = 'Pharmacy Expiry Exclusion (Bonus Adjustment)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False,
                       readonly=True, default='New', tracking=True)
    expiry_date = fields.Date(string='Date of Expiry', required=True,
                              default=fields.Date.context_today,
                              tracking=True,
                              help='Date the loss occurred. Determines '
                                   'which monthly bonus period the '
                                   'exclusion applies to.')
    year = fields.Integer(string='Year', compute='_compute_year_month',
                          store=True, index=True)
    month = fields.Integer(string='Month', compute='_compute_year_month',
                           store=True, index=True)
    product_id = fields.Many2one('product.product', string='Product',
                                 tracking=True)
    lot_id = fields.Many2one('stock.lot', string='Batch / Lot',
                             tracking=True)
    quantity = fields.Float(string='Quantity', tracking=True)
    excluded_value = fields.Float(
        string='Excluded Value', required=True, tracking=True,
        help='Stock value to remove from the bonus rate for this period.')
    reason = fields.Selection(
        selection=[
            ('equipment_failure', 'Equipment Failure (e.g. fridge breakdown)'),
            ('short_dated_delivery', 'Short-Dated Supplier Delivery'),
            ('recall', 'Product Recall'),
            ('damage', 'Damage in Transit'),
            ('regulatory', 'Regulatory Withdrawal'),
            ('other', 'Other (specify in notes)'),
        ], string='Reason', required=True, tracking=True)
    note = fields.Text(string='Notes')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ], string='Status', default='draft', tracking=True, required=True)
    requested_by = fields.Many2one(
        'res.users', string='Requested By', tracking=True,
        default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', string='Approved By',
                                  readonly=True, tracking=True)
    approved_on = fields.Datetime(string='Approved On', readonly=True,
                                  tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 required=True, index=True)

    @api.depends('expiry_date')
    def _compute_year_month(self):
        for rec in self:
            if rec.expiry_date:
                rec.year = rec.expiry_date.year
                rec.month = rec.expiry_date.month
            else:
                rec.year = 0
                rec.month = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pharmacy.expiry.exclusion') or 'EXCL/0001'
        return super().create(vals_list)

    def action_approve(self):
        """Approve the exclusion so it is deducted from the bonus rate."""
        if not self.env.user.has_group(
                'shafic_pharmacy_reports.group_pharmacy_admin'):
            raise UserError(_(
                'Only a Pharmacy Admin can approve an exclusion.'))
        for rec in self:
            if rec.state == 'approved':
                continue
            if not rec.excluded_value or rec.excluded_value <= 0:
                raise UserError(_(
                    'An exclusion must have a positive excluded value.'))
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_on': fields.Datetime.now(),
            })

    def action_reject(self):
        """Reject the exclusion; it will not affect the bonus rate."""
        if not self.env.user.has_group(
                'shafic_pharmacy_reports.group_pharmacy_admin'):
            raise UserError(_(
                'Only a Pharmacy Admin can reject an exclusion.'))
        for rec in self:
            rec.write({
                'state': 'rejected',
                'approved_by': self.env.user.id,
                'approved_on': fields.Datetime.now(),
            })

    def action_reset_to_draft(self):
        """Send the exclusion back to draft for amendment."""
        for rec in self:
            rec.write({
                'state': 'draft',
                'approved_by': False,
                'approved_on': False,
            })
