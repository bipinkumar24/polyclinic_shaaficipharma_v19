# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PharmacyPrescription(models.Model):
    _name = 'pharmacy.prescription'
    _description = 'Pharmacy Prescription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'prescription_date desc, id desc'

    name = fields.Char(
        string='Prescription No.', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    prescription_date = fields.Date(
        string='Prescription Date', required=True,
        default=fields.Date.context_today)
    doctor_id = fields.Many2one(
        'res.partner', string='Doctor', required=True,
        domain=[('is_doctor', '=', True)], tracking=True)
    patient_id = fields.Many2one(
        'res.partner', string='Patient', required=True, tracking=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch')
    pharmacist_id = fields.Many2one(
        'res.users', string='Dispensing Pharmacist',
        default=lambda self: self.env.user)
    line_ids = fields.One2many(
        'pharmacy.prescription.line', 'prescription_id',
        string='Prescription Lines')
    pos_order_ids = fields.One2many(
        'pos.order', 'prescription_id', string='POS Orders')
    pos_order_count = fields.Integer(
        compute='_compute_pos_order_count', string='POS Orders')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('validated', 'Validated'),
            ('dispensed', 'Dispensed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status', default='draft', tracking=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    note = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pharmacy.prescription') or _('New')
        return super().create(vals_list)

    def _compute_pos_order_count(self):
        for rec in self:
            rec.pos_order_count = len(rec.pos_order_ids)

    def action_validate(self):
        self.write({'state': 'validated'})

    def action_dispense(self):
        self.write({'state': 'dispensed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_pos_orders(self):
        self.ensure_one()
        return {
            'name': _('POS Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.pos_order_ids.ids)],
        }


class PharmacyPrescriptionLine(models.Model):
    _name = 'pharmacy.prescription.line'
    _description = 'Pharmacy Prescription Line'

    prescription_id = fields.Many2one(
        'pharmacy.prescription', string='Prescription', required=True,
        ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Medicine', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    dosage = fields.Char(string='Dosage Instructions')
    duration_days = fields.Integer(string='Duration (days)')
    is_controlled = fields.Boolean(
        related='product_id.is_controlled_drug', string='Controlled')
