# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DirectPrintWizard(models.TransientModel):
    _name = 'odoo.leeno.direct.print.wizard'
    _description = 'Direct Print Wizard'

    report_id = fields.Many2one(
        'ir.actions.report',
        string='Report',
        domain="[('model', '=', model)]",
        required=True,
    )
    report_ref = fields.Char(string='Report Reference')
    res_ids = fields.Char(string='Record IDs')
    model = fields.Char(string='Model')
    record_count = fields.Integer(string='Records', compute='_compute_record_count')

    @api.depends('res_ids')
    def _compute_record_count(self):
        for rec in self:
            try:
                ids = json.loads(rec.res_ids) if rec.res_ids else []
                rec.record_count = len(ids)
            except (json.JSONDecodeError, TypeError):
                rec.record_count = 0

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Get model from context
        model = self._context.get('default_model') or self._context.get('active_model')
        res['model'] = model

        # Get record IDs
        res_ids = self._context.get('default_res_ids') or self._context.get('active_ids') or []
        if self._context.get('active_id') and not res_ids:
            res_ids = [self._context.get('active_id')]
        res['res_ids'] = json.dumps(res_ids)

        # Get report from context or find first available for model
        report_ref = self._context.get('default_report_ref')
        if report_ref:
            res['report_ref'] = report_ref
            report = self._get_report_from_ref(report_ref)
            if report:
                res['report_id'] = report.id
        elif model:
            reports = self.env['ir.actions.report'].search([('model', '=', model)], limit=1)
            if reports:
                res['report_id'] = reports.id

        return res

    def _get_report_from_ref(self, report_ref):
        """Get report record from reference (xml_id or id_xxx format)."""
        if not report_ref:
            return False
        try:
            if report_ref.startswith('id_'):
                rid = int(report_ref[3:])
                return self.env['ir.actions.report'].browse(rid)
            else:
                return self.env.ref(report_ref)
        except Exception:
            return False

    def action_print(self):
        """Open the browser print dialog with the selected report PDF."""
        self.ensure_one()

        if not self.report_id:
            raise UserError(_('Please select a report to print.'))

        try:
            res_ids = json.loads(self.res_ids) if self.res_ids else []
            if not res_ids:
                raise UserError(_('No records to print.'))
        except (json.JSONDecodeError, TypeError):
            raise UserError(_('Invalid record IDs.'))

        # Build the PDF URL and trigger the browser print client action
        ids_str = ','.join(str(rid) for rid in res_ids)
        report_url = '/report/pdf/%s/%s' % (self.report_id.report_name, ids_str)

        return {
            'type': 'ir.actions.client',
            'tag': 'leeno_direct_print_browser',
            'params': {
                'url': report_url,
                'title': self.report_id.name or 'Document',
            },
        }


