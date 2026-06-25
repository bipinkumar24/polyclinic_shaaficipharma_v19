# -*- coding: utf-8 -*-

from odoo import api, fields, models ,_
from odoo.exceptions import UserError


class ACSPatient(models.Model):
	_inherit = 'hms.patient'

	new_insurance_company_id = fields.Many2one('hms.insurance.company', string="Insurance Company")