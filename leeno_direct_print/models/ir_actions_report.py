# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    use_leeno_direct_print = fields.Boolean(
        string='Use Direct Print',
        default=False,
        help='If enabled, clicking this report will open the browser print '
             'dialog instead of downloading the PDF.',
    )

    def report_action(self, docids, data=None, config=True):
        """Override to intercept and open the browser print dialog."""
        if not self.use_leeno_direct_print:
            return super().report_action(docids, data=data, config=config)

        # Resolve active_ids
        if docids:
            if isinstance(docids, models.Model):
                active_ids = docids.ids
            elif isinstance(docids, int):
                active_ids = [docids]
            elif isinstance(docids, list):
                active_ids = docids
            else:
                active_ids = []
        else:
            active_ids = self.env.context.get('active_ids', [])

        # Get report reference
        report_ref = self.get_external_id().get(self.id, '')
        if not report_ref:
            report_ref = 'id_%s' % self.id

        return {
            'name': _('Print Document'),
            'type': 'ir.actions.act_window',
            'res_model': 'odoo.leeno.direct.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_report_ref': report_ref,
                'default_res_ids': active_ids,
                'default_model': self.model,
            },
        }
