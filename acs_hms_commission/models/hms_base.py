# -*- coding: utf-8 -*-

from odoo import fields, models, api, SUPERUSER_ID

class Physician(models.Model):
    _inherit = "hms.physician"

    def commission_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_commission.acs_commission_action")
        action['domain'] = [('partner_id','=',self.partner_id.id)]
        action['context'] = {'default_partner_id': self.partner_id.id, 'search_default_not_invoiced': 1}
        return action


class Appointment(models.Model):
    _inherit = "hms.appointment"

    def create_invoice(self):
        res = super(Appointment, self).create_invoice()
        for rec in self:
            rec.invoice_id.onchange_total_amount()
            rec.invoice_id.onchange_ref_physician()
            rec.invoice_id.onchange_physician()
        return res


class AcsCommissionRule(models.Model):
    _inherit = "acs.commission"

    invoice_patient_id = fields.Many2one('hms.patient', related="invoice_id.patient_id", string='Patient', readonly=True, store=True)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            record.acs_create_sequence(name='ACS HMS Commission', code='acs.commission', prefix='COMM')
            record.acs_create_sequence(name='Commission Summary Sheet', code='acs.commission.sheet', prefix='CS')
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: