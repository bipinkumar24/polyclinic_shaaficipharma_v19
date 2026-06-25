# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class InsuranceClaim(models.Model):
    _inherit = 'hms.insurance.claim'

    radiology_request_id = fields.Many2one('acs.radiology.request', string='Radiology Request')
    claim_for = fields.Selection(selection_add=[('radiology', 'Radiology')])


class InsurancePlan(models.Model):
    _inherit = 'acs.insurance.plan'

    allow_radiology_insurance = fields.Boolean(string="Insured Radiology", default=False)
    radiology_insurance_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fix', 'Fix-amount')], 'Radiology Insurance Type', default='percentage', required=True)
    radiology_insurance_amount = fields.Float(string="Radiology Co-payment", help="The patient should pay specific amount 50QR")
    radiology_insurance_percentage = fields.Float(string="Radiology Insured Percentage")
    radiology_insurance_limit = fields.Float(string="Radiology Insurance Limit")
    radiology_create_claim = fields.Boolean(string="Radiology Create Claim", default=False)


class Insurance(models.Model):
    _inherit = 'hms.patient.insurance'

    allow_radiology_insurance = fields.Boolean(string="Insured Radiology", default=False)
    radiology_insurance_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fix', 'Fix-amount')], 'Radiology Insurance Type', default='percentage', required=True)
    radiology_insurance_amount = fields.Float(string="Radiology Co-payment", help="The patient should pay specific amount 50QR")
    radiology_insurance_percentage = fields.Float(string="Radiology Insured Percentage")
    radiology_insurance_limit = fields.Float(string="Radiology Insurance Limit")
    radiology_create_claim = fields.Boolean(string="Radiology Create Claim", default=False)

    @api.onchange('insurance_plan_id')
    def onchange_insurance_plan(self):
        super().onchange_insurance_plan()
        if self.insurance_plan_id:
            plan_id = self.insurance_plan_id
            self.allow_radiology_insurance = plan_id.allow_radiology_insurance
            self.radiology_insurance_type = plan_id.radiology_insurance_type
            self.radiology_insurance_amount = plan_id.radiology_insurance_amount
            self.radiology_insurance_percentage = plan_id.radiology_insurance_percentage
            self.radiology_insurance_limit = plan_id.radiology_insurance_limit
            self.radiology_create_claim = plan_id.radiology_create_claim