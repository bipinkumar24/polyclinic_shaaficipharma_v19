# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PharmacyAutoPreparedOrder(models.Model):
    """Audit log of purchase orders auto-prepared as drafts.

    Every time the daily cron creates a draft PO for a hot product
    that's running low, a row goes here recording what was prepared,
    why, and which draft PO it produced. Lets the team see what the
    system suggested even after the draft is confirmed, rejected, or
    deleted.

    The draft PO itself is a standard purchase.order — Odoo's normal
    workflow takes over from there. This model is just the
    explanation/trail.
    """
    _name = 'pharmacy.auto.prepared.order'
    _description = 'Pharmacy Auto-Prepared Purchase Order Log'
    _order = 'prepared_on desc, id desc'

    name = fields.Char(string='Reference', compute='_compute_name',
                       store=True)
    prepared_on = fields.Datetime(string='Prepared On', readonly=True,
                                  default=fields.Datetime.now, required=True)
    purchase_order_id = fields.Many2one('purchase.order',
                                        string='Draft PO',
                                        readonly=True, ondelete='set null')
    po_state = fields.Selection(related='purchase_order_id.state',
                                string='PO Status', readonly=True)
    supplier_id = fields.Many2one('res.partner', string='Supplier',
                                  readonly=True, required=True)
    line_count = fields.Integer(string='Lines', readonly=True)
    total_amount = fields.Float(string='Total Amount', readonly=True,
                                digits=(16, 2))
    reason = fields.Text(string='Reasoning', readonly=True,
                         help='Why each product was included, with the '
                              'days-of-cover and velocity figures used '
                              'at the time of preparation.')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 required=True, index=True)

    @api.depends('purchase_order_id', 'supplier_id', 'prepared_on')
    def _compute_name(self):
        for rec in self:
            if rec.purchase_order_id:
                rec.name = 'Auto: %s' % rec.purchase_order_id.name
            elif rec.supplier_id:
                rec.name = 'Auto-prep for %s' % rec.supplier_id.name
            else:
                rec.name = 'Auto-prepared order'

    def action_open_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.purchase_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
