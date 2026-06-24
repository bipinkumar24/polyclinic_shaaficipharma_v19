# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import AccessError


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_acs_radiology_test_total = fields.Boolean('New Radiology Tests')
    kpi_acs_radiology_test_total_value = fields.Integer(compute='_compute_kpi_acs_radiology_test_total_value')

    def _compute_kpi_acs_radiology_test_total_value(self):
        if not self.env.user.has_group('acs_hms_base.group_hms_user'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            record.kpi_acs_radiology_test_total_value = self.env['patient.radiology.test'].search_count([('company_id', '=', company.id), ('date_analysis', '>=', start), ('date_analysis', '<', end), ('state', 'not in', ['cancel'])])

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_acs_radiology_test_total'] = 'acs_radiology.action_radiology_result&menu_id=%s' % self.env.ref('acs_radiology.menu_radiology_test_result').id
        return res