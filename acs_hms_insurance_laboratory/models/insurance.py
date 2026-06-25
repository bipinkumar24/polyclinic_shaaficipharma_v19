# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class InsuranceClaim(models.Model):
    _inherit = 'hms.insurance.claim'

    laboratory_request_id = fields.Many2one('acs.laboratory.request', string='Laboratory Request')
    claim_for = fields.Selection(selection_add=[('laboratory', 'Laboratory')])


class InsurancePlan(models.Model):
    _inherit = 'acs.insurance.plan'

    allow_laboratory_insurance = fields.Boolean(string="Insured Laboratory", default=False)
    lab_insurance_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fix', 'Fix-amount')], 'Laboratory Insurance Type', default='percentage', required=True)
    lab_insurance_amount = fields.Float(string="Laboratory Co-payment", help="The patient should pay specific amount 50QR")
    lab_insurance_percentage = fields.Float(string="Laboratory Insured Percentage")
    lab_insurance_limit = fields.Float(string="Laboratory Insurance Limit")
    lab_create_claim = fields.Boolean(string="Laboratory Create Claim", default=False)


class Insurance(models.Model):
    _inherit = 'hms.patient.insurance'

    allow_laboratory_insurance = fields.Boolean(string="Insured Laboratory", default=False)
    lab_insurance_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fix', 'Fix-amount')], 'Laboratory Insurance Type', default='percentage', required=True)
    lab_insurance_amount = fields.Float(string="Laboratory Co-payment", help="The patient should pay specific amount 50QR")
    lab_insurance_percentage = fields.Float(string="Laboratory Insured Percentage")
    lab_insurance_limit = fields.Float(string="Laboratory Insurance Limit")
    lab_create_claim = fields.Boolean(string="Laboratory Create Claim", default=False)

    @api.onchange('insurance_plan_id')
    def onchange_insurance_plan(self):
        super().onchange_insurance_plan()
        if self.insurance_plan_id:
            plan_id = self.insurance_plan_id
            self.allow_laboratory_insurance = plan_id.allow_laboratory_insurance
            self.lab_insurance_type = plan_id.lab_insurance_type
            self.lab_insurance_amount = plan_id.lab_insurance_amount
            self.lab_insurance_percentage = plan_id.lab_insurance_percentage
            self.lab_insurance_limit = plan_id.lab_insurance_limit
            self.lab_create_claim = plan_id.lab_create_claim