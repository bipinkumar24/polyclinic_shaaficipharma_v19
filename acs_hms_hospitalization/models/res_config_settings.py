# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class ResCompany(models.Model):
    _inherit = "res.company"

    acs_hospitalization_usage_location_id = fields.Many2one('stock.location', 
        string='Hospitalization Usage Location for Consumed Products')
    acs_hospitalization_stock_location_id = fields.Many2one('stock.location', 
        string='Hospitalization Stock Location for Consumed Products')
    allow_bed_reservation = fields.Boolean('Allow Bed Reservation')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    acs_hospitalization_usage_location_id = fields.Many2one('stock.location', 
        related='company_id.acs_hospitalization_usage_location_id',
        domain=[('usage','=','customer')],
        string='Hospitalization Usage Location for Consumed Products', 
        ondelete='cascade', help='Usage Location for Consumed Products', readonly=False)
    acs_hospitalization_stock_location_id = fields.Many2one('stock.location', 
        related='company_id.acs_hospitalization_stock_location_id',
        domain=[('usage','=','internal')],
        string='Hospitalization Stock Location for Consumed Products', 
        ondelete='cascade', help='Stock Location for Consumed Products', readonly=False)
    allow_bed_reservation = fields.Boolean('Allow Bed Reservation',
        related='company_id.allow_bed_reservation',
        help='Allow bed Reservation', readonly=False)