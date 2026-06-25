# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ExpiryReportWizard(models.TransientModel):
    _name = 'pharmacy.expiry.report.wizard'
    _description = 'Pharmacy Expiry Report Wizard'

    expiry_bucket = fields.Selection(
        selection=[
            ('expired', 'Expired'),
            ('30', 'Within 30 Days'),
            ('60', 'Within 60 Days'),
            ('90', 'Within 90 Days'),
            ('180', 'Within 180 Days'),
            ('all', 'All Near-Expiry'),
        ], string='Expiry Window', default='90', required=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category')

    def _build_domain(self):
        domain = []
        if self.expiry_bucket == 'expired':
            domain.append(('expiry_bucket', '=', 'expired'))
        elif self.expiry_bucket == '30':
            domain.append(('expiry_bucket', 'in', ('expired', '30')))
        elif self.expiry_bucket == '60':
            domain.append(('expiry_bucket', 'in', ('expired', '30', '60')))
        elif self.expiry_bucket == '90':
            domain.append(('expiry_bucket', 'in',
                           ('expired', '30', '60', '90')))
        elif self.expiry_bucket == '180':
            domain.append(('expiry_bucket', 'in',
                           ('expired', '30', '60', '90', '180')))
        else:
            domain.append(('expiry_bucket', '!=', 'ok'))
        if self.pharmacy_category_id:
            domain.append(('pharmacy_category_id', '=', self.pharmacy_category_id.id))
        return domain

    def action_view_report(self):
        """Open the expiry report filtered by wizard criteria."""
        self.ensure_one()
        return {
            'name': _('Expiry Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'report.pharmacy.expiry',
            'view_mode': 'list,pivot,graph',
            'domain': self._build_domain(),
            'context': {'search_default_group_bucket': 1},
        }

    def action_print_pdf(self):
        """Print the expiry report as a PDF."""
        self.ensure_one()
        records = self.env['report.pharmacy.expiry'].sudo().search(
            self._build_domain())
        return self.env.ref(
            'shafic_pharmacy_reports.action_report_pharmacy_expiry'
        ).report_action(records)
