# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PharmacyStockCount(models.Model):
    """Physical stock count and reconciliation against system quantity.

    Captures a snapshot of what was counted versus what Odoo thought
    was on hand. Variances are computed per line; the header totals
    the absolute variance value. Approving a count is a deliberate
    act — the figures stay visible afterwards as a record of the
    reconciliation, but Odoo's inventory itself is not auto-adjusted.
    A manager records the action on the variance afterwards.
    """
    _name = 'pharmacy.stock.count'
    _description = 'Pharmacy Stock Count'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'count_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, copy=False,
                       readonly=True, default='New', tracking=True)
    count_date = fields.Date(string='Count Date', required=True,
                             default=fields.Date.context_today,
                             tracking=True)
    counted_by = fields.Many2one(
        'res.users', string='Counted By', tracking=True,
        default=lambda self: self.env.user)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Submitted'),
            ('approved', 'Approved'),
        ], string='Status', default='draft', tracking=True, required=True)
    note = fields.Text(string='Notes')
    line_ids = fields.One2many('pharmacy.stock.count.line', 'count_id',
                               string='Lines')

    line_count = fields.Integer(string='Items Counted',
                                compute='_compute_totals', store=True)
    variance_value_abs = fields.Float(
        string='Total Variance ($, abs)', compute='_compute_totals',
        store=True, digits=(16, 2),
        help='Sum of |variance value|. A useful headline figure for '
             'how much money the count moved.')
    variance_value_net = fields.Float(
        string='Net Variance ($)', compute='_compute_totals', store=True,
        digits=(16, 2),
        help='Net variance value: positive = system understated stock; '
             'negative = system overstated stock (shrinkage).')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 required=True, index=True)

    @api.depends('line_ids', 'line_ids.variance_value')
    def _compute_totals(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.variance_value_abs = sum(
                abs(l.variance_value) for l in rec.line_ids)
            rec.variance_value_net = sum(
                l.variance_value for l in rec.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pharmacy.stock.count') or 'COUNT/0001'
        return super().create(vals_list)

    def action_capture_system_qty(self):
        """Snapshot the current Odoo on-hand qty onto each draft line."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    'System quantities can only be captured on a draft '
                    'count.'))
            for line in rec.line_ids:
                line.system_qty = line._read_current_system_qty()

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_(
                    'Add at least one line before submitting the count.'))
            # Snapshot system quantities if not already captured
            for line in rec.line_ids:
                if not line.system_qty:
                    line.system_qty = line._read_current_system_qty()
            rec.state = 'done'

    def action_approve(self):
        if not self.env.user.has_group(
                'shafic_pharmacy_reports.group_pharmacy_admin'):
            raise UserError(_(
                'Only a Pharmacy Admin can approve a stock count.'))
        for rec in self:
            rec.state = 'approved'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'


class PharmacyStockCountLine(models.Model):
    _name = 'pharmacy.stock.count.line'
    _description = 'Pharmacy Stock Count Line'
    _order = 'count_id, id'

    count_id = fields.Many2one('pharmacy.stock.count', string='Count',
                               required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product',
                                 required=True)
    lot_id = fields.Many2one('stock.lot', string='Batch / Lot')
    counted_qty = fields.Float(string='Counted', required=True)
    system_qty = fields.Float(string='System Qty',
                              help='Odoo on-hand quantity at the time '
                                   'the count was captured.')
    variance = fields.Float(string='Variance', compute='_compute_variance',
                            store=True, digits=(12, 2))
    unit_cost = fields.Float(string='Unit Cost',
                             compute='_compute_unit_cost', store=True,
                             digits=(12, 4))
    variance_value = fields.Float(
        string='Variance Value ($)', compute='_compute_variance',
        store=True, digits=(16, 2))
    state = fields.Selection(related='count_id.state', store=True)
    company_id = fields.Many2one(related='count_id.company_id', store=True)

    @api.depends('counted_qty', 'system_qty', 'unit_cost')
    def _compute_variance(self):
        for rec in self:
            rec.variance = (rec.counted_qty or 0.0) - (rec.system_qty or 0.0)
            rec.variance_value = rec.variance * (rec.unit_cost or 0.0)

    @api.depends('product_id', 'count_id.company_id')
    def _compute_unit_cost(self):
        for rec in self:
            if rec.product_id and rec.count_id.company_id:
                rec.unit_cost = self.env[
                    'product.effective.cost'
                ].get_moving_avg_cost_one(
                    rec.product_id.id, rec.count_id.company_id.id)
            else:
                rec.unit_cost = 0.0

    def _read_current_system_qty(self):
        """Return the live on-hand qty for this line's product+lot."""
        self.ensure_one()
        domain = [
            ('product_id', '=', self.product_id.id),
            ('location_id.usage', '=', 'internal'),
            ('company_id', '=', self.count_id.company_id.id),
        ]
        if self.lot_id:
            domain.append(('lot_id', '=', self.lot_id.id))
        quants = self.env['stock.quant'].sudo().search(domain)
        return sum(quants.mapped('quantity'))
