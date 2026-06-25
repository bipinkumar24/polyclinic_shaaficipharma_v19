# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PharmacyExpiryAction(models.Model):
    """Record of a deliberate action taken on near-expiry stock.

    Each row represents one of: a discount applied to clear stock, a
    supplier return arranged, a transfer to another location, or a
    manual write-off acknowledgement. These are the "real catches" the
    bonus rate rewards — without this log, the KPI is a proxy.

    Rows are created from buttons on the expiry report (or manually
    from this menu) and are read by the bonus scorecard when computing
    the catch-early KPI.
    """
    _name = 'pharmacy.expiry.action'
    _description = 'Pharmacy Expiry Catch Action'
    _order = 'action_date desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name',
                               store=True)
    action_date = fields.Date(string='Action Date', required=True,
                              default=fields.Date.context_today,
                              index=True)
    year = fields.Integer(string='Year', compute='_compute_year_month',
                          store=True, index=True)
    month = fields.Integer(string='Month', compute='_compute_year_month',
                           store=True, index=True)
    action_type = fields.Selection(
        selection=[
            ('discount', 'Discount Applied'),
            ('supplier_return', 'Supplier Return'),
            ('transfer', 'Internal Transfer'),
            ('clearance', 'Marked for Clearance'),
            ('writeoff', 'Acknowledged Write-off'),
        ], string='Action', required=True)
    product_id = fields.Many2one('product.product', string='Product',
                                 required=True)
    lot_id = fields.Many2one('stock.lot', string='Batch / Lot')
    quantity = fields.Float(string='Quantity')
    value_at_risk = fields.Float(
        string='Value at Risk', required=True,
        help='Stock value that was at risk of expiry when the action '
             'was taken. Used by the bonus catch-early KPI.')
    expiry_date = fields.Date(string='Lot Expiry Date')
    note = fields.Text(string='Notes')
    user_id = fields.Many2one('res.users', string='Recorded By',
                              default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 required=True, index=True)

    @api.depends('action_type', 'product_id', 'action_date')
    def _compute_display_name(self):
        labels = dict(self._fields['action_type'].selection)
        for rec in self:
            rec.display_name = '%s — %s (%s)' % (
                labels.get(rec.action_type, rec.action_type or ''),
                rec.product_id.display_name or '',
                rec.action_date or '')

    @api.depends('action_date')
    def _compute_year_month(self):
        for rec in self:
            if rec.action_date:
                rec.year = rec.action_date.year
                rec.month = rec.action_date.month
            else:
                rec.year = 0
                rec.month = 0
