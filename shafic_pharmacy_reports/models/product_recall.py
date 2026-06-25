# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProductRecall(models.Model):
    _name = 'pharmacy.product.recall'
    _description = 'Pharmacy Product Recall'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'recall_date desc, id desc'

    name = fields.Char(
        string='Recall Ref.', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    recall_date = fields.Date(
        string='Recall Date', required=True,
        default=fields.Date.context_today)
    product_id = fields.Many2one(
        'product.product', string='Recalled Product', required=True,
        tracking=True)
    lot_ids = fields.Many2many('stock.lot', string='Affected Batches / Lots')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    reason = fields.Text(string='Recall Reason', required=True)
    severity = fields.Selection(
        selection=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High / Critical'),
        ],
        string='Severity', default='medium', tracking=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        string='Status', default='draft', tracking=True)
    affected_qty = fields.Float(
        string='Affected Quantity', compute='_compute_traceability',
        store=False)
    affected_customer_ids = fields.Many2many(
        'res.partner', string='Affected Customers',
        compute='_compute_traceability', store=False)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pharmacy.product.recall') or _('New')
        return super().create(vals_list)

    @api.depends('product_id', 'lot_ids')
    def _compute_traceability(self):
        """Trace recalled lots through POS sales to identify affected
        customers and total dispensed quantity."""
        pos_line = self.env['pos.order.line']
        for recall in self:
            customers = self.env['res.partner']
            qty = 0.0
            if recall.product_id:
                domain = [('product_id', '=', recall.product_id.id)]
                lines = pos_line.search(domain)
                for line in lines:
                    pack_lots = line.pack_lot_ids.mapped('lot_id') \
                        if 'pack_lot_ids' in line._fields else \
                        self.env['stock.lot']
                    if recall.lot_ids and pack_lots and \
                            not (pack_lots & recall.lot_ids):
                        continue
                    qty += line.qty
                    if line.order_id.partner_id:
                        customers |= line.order_id.partner_id
            recall.affected_qty = qty
            recall.affected_customer_ids = [(6, 0, customers.ids)]

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_notify_customers(self):
        """Schedule a follow-up activity for each affected customer."""
        self.ensure_one()
        template = self.env.ref(
            'shafic_pharmacy_reports.mail_template_product_recall',
            raise_if_not_found=False)
        for partner in self.affected_customer_ids:
            if template:
                template.send_mail(self.id, force_send=False,
                                    email_values={'email_to': partner.email})
        return True
