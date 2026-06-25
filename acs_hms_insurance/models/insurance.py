# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AcsInsurancePlan(models.Model):
    _name = 'acs.insurance.plan'
    _description = "Insurance Plan"
    _order = "sequence"

    name = fields.Text(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string="Active", default=True)
    insurance_company_id = fields.Many2one('hms.insurance.company', string ="Insurance Company", required=True)

    allow_appointment_insurance = fields.Boolean(string="Insured Appointments")
    app_insurance_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fix', 'Fix-amount'),
        ('percentage_with_max', 'Percentage with max-amount')], 'Appointment Insurance Type', default='percentage', required=True)
    app_insurance_amount = fields.Float(string="Appointment Co-payment", help="The patient should pay specific amount 50QR")
    app_insurance_percentage = fields.Float(string="Appointment Insured Percentage")
    app_insurance_limit = fields.Float(string="Appointment Insurance Limit")
    create_claim = fields.Boolean(string="Appointment Create Claim")
    
    allow_pharmacy_insurance = fields.Boolean(string="Insured Pharmacy", default=False)
    pha_insurance_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fix', 'Fix-amount')], 'Pharmacy Insurance Type', default='percentage', required=True)
    pha_insurance_amount = fields.Float(string="Pharmacy Co-payment", help="The patient should pay specific amount 50QR")
    pha_insurance_percentage = fields.Float(string="Pharmacy Insured Percentage")
    pha_insurance_limit = fields.Float(string="Pharmacy Insurance Limit")
    pha_create_claim = fields.Boolean(string="Pharmacy Create Claim", default=False)
    policy_rule_ids = fields.One2many("acs.insurance.policy.rule", "insurance_plan_id", string="Policy Patient Share Rules")
    patient_share_by_rule = fields.Boolean("Patient Share Based on Rules", default=False)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',
        help="If you change the pricelist, only newly added lines will be affected.")
    note = fields.Text("Notes")
    excluded_product_ids = fields.Many2many('product.template', 'acs_product_template_insurance_plan_rel', 'plan_id', 'product_id', string="Excluded Products")


class AcsInsurancePolicyRules(models.Model):
    _name = 'acs.insurance.policy.rule'
    _description = 'Patient Share Rules'
    _order = "sequence"

    sequence = fields.Integer(string='Sequence', default=50)
    insurance_company_id = fields.Many2one('hms.insurance.company', string ="Insurance Company")
    insurance_policy_id = fields.Many2one('hms.patient.insurance', string ="Insurance Policy")
    insurance_plan_id = fields.Many2one('acs.insurance.plan', string ="Insurance Plan")
    rule_on = fields.Selection([
        ('product_category', 'Product Category'),
        ('product', 'Product'),
    ], string='Rule On', copy=False, default='product_category', required=True)
    product_category_id = fields.Many2one('product.category', string='Product Category')
    product_id = fields.Many2one('product.template', string='Product')
    rule_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('amount', 'Amount'), 
    ], string='Type', default='percentage')
    percentage = fields.Float('Percentage')
    amount = fields.Float('Amount')
    full_cover = fields.Boolean(string="100%")
    description = fields.Text("Description")

    @api.constrains('rule_type','percentage','amount')
    def _check_allocation(self):
        for rec in self:
            if rec.rule_type=='percentage' and rec.full_cover:
                pass
            elif rec.rule_type=='percentage' and (rec.percentage>100 or rec.percentage<=0):
                raise ValidationError((_("Percentage can not be more than 100 or zero.")))
            elif rec.rule_type=='amount' and (rec.amount<0):
                raise ValidationError((_("Amount can not be negative.")))

    @api.onchange('full_cover')
    def onchange_full_cover(self):
        if self.full_cover:
            self.percentage = 100

class InsuranceCompany(models.Model):
    _name = 'hms.insurance.company'
    _description = "Insurance Company"
    _inherits = {
        'res.partner': 'partner_id',
    }
    
    description = fields.Text()
    partner_id = fields.Many2one('res.partner', 'Partner', ondelete='restrict', required=True)
    active = fields.Boolean(string="Active", default=True)
    patient_share_product_id = fields.Many2one('product.product', 'Patient Share Product', ondelete='restrict')
    policy_rule_ids = fields.One2many("acs.insurance.policy.rule", "insurance_company_id", string="Policy Patient Share Rules")
    excluded_product_ids = fields.Many2many('product.template', 'acs_product_template_insurance_company_rel', 'insurance_company_id', 'product_id', string="Excluded Products")

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id:
            self.name = self.partner_id.name

    #ACS NOTE: To avoid dependency issue this code is here. 
    #Move to related module if new one is created.
    @api.model
    def GetInsuranceCompany(self, args, **kwargs):
        """
        var model = 'hms.insurance.company';
        var method = 'GetInsuranceCompany';

        var args = [
            { }
        ];
        """
        insurance_companies = self.sudo().search([])
        insurance_company_data = []
        for ic in insurance_companies:
            insurance_company_data.append({
                'id': ic.id,
                'name': ic.name,
            })
        return insurance_company_data


class Insurance(models.Model):
    _name = 'hms.patient.insurance'
    _description = "Patient Insurance"
    _rec_name = 'policy_number'
    
    patient_id = fields.Many2one('hms.patient', string ='Patient', ondelete='restrict', required=True)
    insurance_company_id = fields.Many2one('hms.insurance.company', string ="Insurance Company", required=True)
    insurance_plan_id = fields.Many2one('acs.insurance.plan', string ="Insurance Plan")
    policy_number = fields.Char(string ="Policy Number", required=True)
    insured_value = fields.Float(string ="Insured Value")
    validity = fields.Date(string="Validity")
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text("Notes")

    allow_appointment_insurance = fields.Boolean(string="Insured Appointments")
    app_insurance_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fix', 'Fix-amount'),
        ('percentage_with_max', 'Percentage with max-amount')], 'Appointment Insurance Type', default='percentage', required=True)
    app_insurance_amount = fields.Float(string="Appointment Co-payment", help="The patient should pay specific amount 50QR")
    app_insurance_percentage = fields.Float(string="Appointment Insured Percentage")
    app_insurance_limit = fields.Float(string="Appointment Insurance Limit")
    create_claim = fields.Boolean(string="Appointment Create Claim")
    
    allow_pharmacy_insurance = fields.Boolean(string="Insured Pharmacy", default=False)
    pha_insurance_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fix', 'Fix-amount')], 'Pharmacy Insurance Type', default='percentage', required=True)
    pha_insurance_amount = fields.Float(string="Pharmacy Co-payment", help="The patient should pay specific amount 50QR")
    pha_insurance_percentage = fields.Float(string="Pharmacy Insured Percentage")
    pha_insurance_limit = fields.Float(string="Pharmacy Insurance Limit")
    pha_create_claim = fields.Boolean(string="Pharmacy Create Claim", default=False)

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',
        help="If you change the pricelist, only newly added lines will be affected.")
    company_id = fields.Many2one('res.company', 'Hospital', default=lambda self: self.env.company)
    patient_share_in_invoice = fields.Boolean("Show Patient Share in Insurance Invoice", default=True)
    patient_share_by_rule = fields.Boolean("Patient Share Based on Rules", default=False)
    policy_rule_ids = fields.One2many("acs.insurance.policy.rule", "insurance_policy_id", string="Policy Patient Share Rules")
    excluded_product_ids = fields.Many2many('product.template', 'acs_product_template_policy_rel', 'policy_id', 'product_id', string="Excluded Products")

    def _compute_display_name(self):
        for rec in self:
            name = rec.policy_number 
            if rec.insurance_plan_id:
                name += ' - ' + rec.insurance_plan_id.name
            elif rec.insurance_company_id:
                name += ' - ' + rec.insurance_company_id.name
            rec.display_name = name

    @api.onchange('insurance_company_id')
    def onchange_insurance_company(self):
        if self.insurance_company_id and self.insurance_company_id.property_product_pricelist:
            self.pricelist_id = self.insurance_company_id.property_product_pricelist.id

    @api.onchange('insurance_plan_id')
    def onchange_insurance_plan(self):
        if self.insurance_plan_id:
            self.policy_rule_ids.unlink()
            plan_id = self.insurance_plan_id
            policy_rule_lines = []
            for line in plan_id.policy_rule_ids:
                policy_rule_lines.append((0,0,{
                    'sequence': line.sequence,
                    'rule_on': line.rule_on or False,
                    'product_category_id': line.product_category_id,
                    'product_id': line.product_id,
                    'rule_type' : line.rule_type,
                    'percentage': line.percentage,
                    'amount': line.amount,
                    'full_cover': line.full_cover,
                }))
            self.patient_share_by_rule = plan_id.patient_share_by_rule
            self.pricelist_id = plan_id.pricelist_id and plan_id.pricelist_id.id
            self.allow_appointment_insurance = plan_id.allow_appointment_insurance
            self.app_insurance_type = plan_id.app_insurance_type
            self.app_insurance_amount = plan_id.app_insurance_amount
            self.app_insurance_percentage = plan_id.app_insurance_percentage
            self.app_insurance_limit = plan_id.app_insurance_limit
            self.create_claim = plan_id.create_claim
            self.allow_pharmacy_insurance = plan_id.allow_pharmacy_insurance
            self.pha_insurance_type = plan_id.pha_insurance_type
            self.pha_insurance_amount = plan_id.pha_insurance_amount
            self.pha_insurance_percentage = plan_id.pha_insurance_percentage
            self.pha_insurance_limit = plan_id.pha_insurance_limit
            self.pha_create_claim = plan_id.pha_create_claim
            self.patient_share_by_rule = plan_id.patient_share_by_rule
            self.policy_rule_ids = policy_rule_lines
            self.excluded_product_ids = excluded_product_ids

    @api.model
    def archive_expired_policy(self):
        records = self.search([('validity','<', fields.Date.today())])
        records.write({'active': False})

    def acs_get_excluded_product_ids(self):
        excluded_product_ids = []
        for rec in self:
            excluded_product_ids += rec.excluded_product_ids.mapped('product_variant_ids').ids
            if rec.insurance_company_id and rec.insurance_company_id.excluded_product_ids:
                excluded_product_ids += rec.insurance_company_id.excluded_product_ids.mapped('product_variant_ids').ids
        return excluded_product_ids


class InsuranceTPA(models.Model):
    _name = 'insurance.tpa'
    _description = "Insurance TPA"
    _inherits = {
        'res.partner': 'partner_id',
    }

    partner_id = fields.Many2one('res.partner', 'Partner', required=True, ondelete='restrict')
    active = fields.Boolean('Active', default=True)


class InsuranceChecklistTemp(models.Model):
    _name = 'hms.insurance.checklist.template'
    _description = "Insurance Checklist Template"

    name = fields.Char('Name')
    active = fields.Boolean('Active', default=True)


class RequiredDocuments(models.Model):
    _name = 'hms.insurance.req.doc'
    _description = "Insurance Req Doc"
    
    name = fields.Char('Name')
    active = fields.Boolean('Active', default=True)


class InsuranceCheckList(models.Model):
    _name="hms.insurance.checklist"
    _description = "Insurance Checklist"

    name = fields.Char(string="Name")
    is_done = fields.Boolean(string="Y/N")
    remark = fields.Char(string="Remarks")
    claim_id = fields.Many2one("hms.insurance.claim", string="Claim")
