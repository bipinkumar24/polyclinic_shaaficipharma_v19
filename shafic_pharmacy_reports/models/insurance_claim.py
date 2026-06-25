# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class InsuranceClaim(models.Model):
    _name = 'pharmacy.insurance.claim'
    _description = 'Pharmacy Insurance Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'claim_date desc, id desc'

    name = fields.Char(
        string='Claim No.', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    claim_date = fields.Date(
        string='Claim Date', required=True,
        default=fields.Date.context_today)
    provider_id = fields.Many2one(
        'res.partner', string='Insurance Provider', required=True,
        domain=[('is_insurance_provider', '=', True)], tracking=True)
    patient_id = fields.Many2one(
        'res.partner', string='Patient', required=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch')
    pos_order_id = fields.Many2one('pos.order', string='POS Order')
    claim_amount = fields.Monetary(
        string='Claimed Amount', required=True,
        currency_field='currency_id')
    approved_amount = fields.Monetary(
        string='Approved Amount', currency_field='currency_id')
    rejected_amount = fields.Monetary(
        string='Rejected Amount', compute='_compute_rejected_amount',
        store=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('partial', 'Partially Approved'),
            ('rejected', 'Rejected'),
            ('paid', 'Paid'),
        ],
        string='Status', default='draft', tracking=True)
    submission_date = fields.Date(string='Submission Date')
    settlement_date = fields.Date(string='Settlement Date')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    note = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pharmacy.insurance.claim') or _('New')
        return super().create(vals_list)

    @api.depends('claim_amount', 'approved_amount', 'state')
    def _compute_rejected_amount(self):
        for claim in self:
            if claim.state in ('rejected', 'partial', 'paid', 'approved'):
                claim.rejected_amount = max(
                    claim.claim_amount - claim.approved_amount, 0.0)
            else:
                claim.rejected_amount = 0.0

    def action_submit(self):
        self.write({
            'state': 'submitted',
            'submission_date': fields.Date.context_today(self),
        })

    def action_approve(self):
        for claim in self:
            if not claim.approved_amount:
                claim.approved_amount = claim.claim_amount
            if claim.approved_amount >= claim.claim_amount:
                claim.state = 'approved'
            elif claim.approved_amount > 0:
                claim.state = 'partial'
            else:
                claim.state = 'rejected'

    def action_reject(self):
        self.write({'state': 'rejected', 'approved_amount': 0.0})

    def action_mark_paid(self):
        self.write({
            'state': 'paid',
            'settlement_date': fields.Date.context_today(self),
        })

    def action_reset_draft(self):
        self.write({'state': 'draft'})
