# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ResCompany(models.Model):
    _inherit = "res.company"

    invoice_discount_product_id = fields.Many2one('product.product', string='Invoice Discount Product')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_discount_product_id = fields.Many2one('product.product', related='company_id.invoice_discount_product_id', string='Invoice Discount Product', readonly=False)

class HmsPatient(models.Model):
    _inherit = 'hms.patient'

    @api.model
    def cron_sync_patient_partners(self):
        """
        Sync HMS Patient → Partner
        - Mark partner as patient
        - Set acs_patient_id
        """

        self.env.cr.execute("""
            UPDATE res_partner rp
            SET
                is_patient = TRUE,
                acs_patient_id = hp.id
            FROM hms_patient hp
            WHERE hp.partner_id = rp.id
        """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: