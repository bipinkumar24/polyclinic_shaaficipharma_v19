# -*- coding: utf-8 -*-
# Part of AlmightyCS See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _


class ResCompany(models.Model):
    _inherit = "res.company"

    acs_radiology_usage_location_id = fields.Many2one('stock.location', 
        string='Usage Location for Consumed Radiology Test Material.')
    acs_radiology_stock_location_id = fields.Many2one('stock.location', 
        string='Stock Location for Consumed Radiology Test Material')
    acs_radiology_result_qrcode = fields.Boolean(string="Print Authentication QrCode on Radiology Result", default=True)
    acs_radiology_invoice_policy = fields.Selection([('any_time', 'Anytime'), ('in_advance', 'Advance'),
        ('in_end', 'At End')], default="any_time", string="Radiology Invoice Policy", required=True)
    acs_check_radiology_payment = fields.Boolean(string="Check Payment Status before Accepting Radiology Request")
    acs_radiology_disclaimer = fields.Text(string="Radiology Disclaimer")
    acs_no_radiology_result = fields.Boolean(string="No Radiology Result", default=False)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    acs_radiology_usage_location_id = fields.Many2one('stock.location', 
        related='company_id.acs_radiology_usage_location_id',
        domain=[('usage','=','customer')],
        string='Usage Location for Consumed Radiology Test Material', readonly=False)
    acs_radiology_stock_location_id = fields.Many2one('stock.location', 
        related='company_id.acs_radiology_stock_location_id',
        domain=[('usage','=','internal')],
        string='Stock Location for Consumed Radiology Test Material', readonly=False)
    acs_radiology_result_qrcode = fields.Boolean(related='company_id.acs_radiology_result_qrcode', string="Print Authentication QrCode on Radiology Result", readonly=False)
    acs_radiology_invoice_policy = fields.Selection(related='company_id.acs_radiology_invoice_policy', string="Radiology Invoice Policy", readonly=False)
    acs_check_radiology_payment = fields.Boolean(related='company_id.acs_check_radiology_payment', string="Check Payment Status before Accepting Radiology Request", readonly=False)
    acs_radiology_disclaimer = fields.Text(related='company_id.acs_radiology_disclaimer', string="Radiology Disclaimer", readonly=False)
    acs_no_radiology_result = fields.Boolean(related='company_id.acs_no_radiology_result', string="No Radiology Result", readonly=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: