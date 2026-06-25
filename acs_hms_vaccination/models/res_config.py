# -*- coding: utf-8 -*-
# Part of AlmightyCS See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    vaccination_invoicing = fields.Boolean("Allow Vaccination Invoicing", default=True)
    acs_vaccination_usage_location_id = fields.Many2one('stock.location', 
        string='Usage Location for Consumed Vaccine.')
    acs_vaccination_stock_location_id = fields.Many2one('stock.location', 
        string='Stock Location for Consumed Vaccine')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vaccination_invoicing = fields.Boolean("Allow Vaccination Invoicing", related='company_id.vaccination_invoicing', readonly=False)
    acs_vaccination_usage_location_id = fields.Many2one('stock.location', 
        related='company_id.acs_vaccination_usage_location_id',
        domain=[('usage','=','customer')],
        string='Usage Location for Consumed Vaccine', readonly=False)
    acs_vaccination_stock_location_id = fields.Many2one('stock.location', 
        related='company_id.acs_vaccination_stock_location_id',
        domain=[('usage','=','internal')],
        string='Stock Location for Consumed acs_vaccination_usage_location_id', readonly=False)