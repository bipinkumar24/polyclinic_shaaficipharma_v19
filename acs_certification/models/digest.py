# -*- coding: utf-8 -*-

from odoo import fields, models, _


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_acs_certification_total = fields.Boolean('New Certification')
    kpi_acs_certification_total_value = fields.Integer(compute='_compute_kpi_acs_certification_total_value')

    def _compute_kpi_acs_certification_total_value(self):
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            certification = self.env['certificate.management'].sudo().search_count([('company_id', '=', company.id), ('date', '>=', start), ('date', '<', end)])
            record.kpi_acs_certification_total_value = certification

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_acs_certification_total'] = 'acs_certification.action_certificate_management&menu_id=%s' % self.env.ref('acs_certification.menu_certificate_management').id
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: