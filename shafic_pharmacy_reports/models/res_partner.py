# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_patient = fields.Boolean(string='Is Patient')
    patient_code = fields.Char(string='Patient Code', copy=False)
    insurance_provider_id = fields.Many2one(
        'res.partner', string='Insurance Provider',
        domain=[('is_insurance_provider', '=', True)])
    is_insurance_provider = fields.Boolean(string='Is Insurance Provider')
    is_doctor = fields.Boolean(string='Is Doctor')
    doctor_license = fields.Char(string='Doctor License No.')
    customer_segment = fields.Selection(
        selection=[
            ('high_value', 'High Value'),
            ('frequent', 'Frequent Buyer'),
            ('insurance', 'Insurance Patient'),
            ('regular', 'Regular'),
            ('new', 'New'),
        ],
        string='Customer Segment', compute='_compute_customer_segment',
        store=True, readonly=True)
    pharmacy_total_spend = fields.Monetary(
        string='Total Pharmacy Spend', compute='_compute_pharmacy_stats',
        currency_field='currency_id')
    pharmacy_visit_count = fields.Integer(
        string='Visit Count', compute='_compute_pharmacy_stats')

    def _compute_pharmacy_stats(self):
        """Aggregate POS purchase totals and visit counts per partner."""
        pos_order = self.env['pos.order']
        for partner in self:
            orders = pos_order.search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ('paid', 'done', 'invoiced')),
            ])
            partner.pharmacy_total_spend = sum(orders.mapped('amount_total'))
            partner.pharmacy_visit_count = len(orders)

    @api.depends('insurance_provider_id')
    def _compute_customer_segment(self):
        """Classify each partner into a customer segment.

        Stored so it can be used as a SQL-view column and a groupable
        dimension. POS spend / visit aggregates are read inline (rather
        than via the non-stored stat fields) so the value is correct at
        compute time; a daily cron refreshes it as POS activity grows.
        """
        pos_order = self.env['pos.order']
        for partner in self:
            orders = pos_order.search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ('paid', 'done', 'invoiced')),
            ])
            total_spend = sum(orders.mapped('amount_total'))
            visit_count = len(orders)
            if partner.insurance_provider_id:
                partner.customer_segment = 'insurance'
            elif total_spend >= 5000:
                partner.customer_segment = 'high_value'
            elif visit_count >= 10:
                partner.customer_segment = 'frequent'
            elif visit_count > 0:
                partner.customer_segment = 'regular'
            else:
                partner.customer_segment = 'new'

    def action_recompute_customer_segment(self):
        """Force a recompute of the customer segment for these partners."""
        self._compute_customer_segment()
