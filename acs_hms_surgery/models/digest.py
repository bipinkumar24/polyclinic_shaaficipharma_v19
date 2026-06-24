# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import AccessError


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_acs_surgery_total = fields.Boolean('New Surgerys')
    kpi_acs_surgery_total_value = fields.Integer(compute='_compute_kpi_acs_surgery_total_value')

    def _compute_kpi_acs_surgery_total_value(self):
        if not self.env.user.has_group('acs_hms_base.group_hms_user'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            surgery = self.env['hms.surgery'].search_count([('company_id', '=', company.id), ('start_date', '>=', start), ('start_date', '<', end), ('state', 'not in', ['cancel'])])
            record.kpi_acs_surgery_total_value = surgery

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_acs_surgery_total'] = 'acs_hms_surgery.action_hms_surgery&menu_id=%s' % self.env.ref('acs_hms_surgery.main_menu_surgery').id
        return res