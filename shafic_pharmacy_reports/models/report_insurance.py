# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyInsurance(models.Model):
    """Insurance billing report - claims submitted/approved/pending/rejected."""
    _name = 'report.pharmacy.insurance'
    _description = 'Pharmacy Insurance Billing Report'
    _auto = False
    _order = 'claim_date desc'

    claim_id = fields.Many2one('pharmacy.insurance.claim',
                               string='Claim', readonly=True)
    claim_no = fields.Char(string='Claim No.', readonly=True)
    claim_date = fields.Date(string='Claim Date', readonly=True)
    provider_id = fields.Many2one('res.partner', string='Insurance Provider',
                                  readonly=True)
    patient_id = fields.Many2one('res.partner', string='Patient',
                                 readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('partial', 'Partially Approved'),
            ('rejected', 'Rejected'),
            ('paid', 'Paid'),
        ], string='Status', readonly=True)
    claim_amount = fields.Float(string='Claimed Amount', readonly=True)
    approved_amount = fields.Float(string='Approved Amount', readonly=True)
    rejected_amount = fields.Float(string='Rejected Amount', readonly=True)
    is_pending = fields.Boolean(string='Pending', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    c.id AS id,
                    c.id AS claim_id,
                    c.name AS claim_no,
                    c.claim_date AS claim_date,
                    c.provider_id AS provider_id,
                    c.patient_id AS patient_id,
                    c.branch_id AS branch_id,
                    c.state AS state,
                    c.claim_amount AS claim_amount,
                    c.approved_amount AS approved_amount,
                    c.rejected_amount AS rejected_amount,
                    CASE WHEN c.state IN ('draft', 'submitted')
                         THEN TRUE ELSE FALSE END AS is_pending,
                    c.company_id AS company_id
                FROM pharmacy_insurance_claim c
            )
        """ % self._table)
