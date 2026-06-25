# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import logging

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class DirectPrintAction(models.AbstractModel):
    _name = 'odoo.leeno.direct.print.action'
    _description = 'Direct Print Action Helper'

    @api.model
    def _get_leeno_direct_print_models(self):
        """Return list of models that should have a Direct Print binding action."""
        return [
            'res.partner',
            'sale.order',
            'account.move',
            'purchase.order',
            'stock.picking',
            'prescription.order',
            'acs.radiology.request',
            'acs.laboratory.request',
            'hms.appointment',
            'acs.patient.laboratory.sample',
            'patient.laboratory.test',
            'patient.radiology.test',
            'hms.treatment',
        ]

    @api.model
    def _get_leeno_direct_print_code_template(self):
        return """
if records:
    action = {
        'name': 'Direct Print',
        'type': 'ir.actions.act_window',
        'res_model': 'odoo.leeno.direct.print.wizard',
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_model': records._name,
            'active_model': records._name,
            'active_ids': records.ids,
            'active_id': records.ids[0] if records.ids else False,
        },
    }
"""

    @api.model
    def _ensure_print_actions(self):
        """Create or repair Direct Print server actions for supported models.

        Idempotent: existing actions are checked and repaired if their
        binding_model_id was cleared (which makes the button disappear).
        """
        code_template = self._get_leeno_direct_print_code_template()
        IrModel = self.env['ir.model']
        IrActionsServer = self.env['ir.actions.server']
        created = []

        for model_name in self._get_leeno_direct_print_models():
            model = IrModel.search([('model', '=', model_name)], limit=1)
            if not model:
                continue

            existing = IrActionsServer.search([
                ('name', '=', 'Direct Print'),
                ('model_id', '=', model.id),
            ], limit=1)

            if existing:
                # Repair: ensure binding is still set
                if not existing.binding_model_id:
                    existing.write({
                        'binding_model_id': model.id,
                        'binding_view_types': 'form,list',
                    })
                    created.append(model_name + ' (repaired)')
                continue

            IrActionsServer.create({
                'name': 'Direct Print',
                'model_id': model.id,
                'binding_model_id': model.id,
                'binding_view_types': 'form,list',
                'state': 'code',
                'code': code_template,
            })
            created.append(model_name)

        return created

    @api.model
    def action_create_print_actions(self):
        """Create Direct Print server actions for supported models (interactive)."""
        created = self._ensure_print_actions()
        msg = (_('Created Direct Print actions for: %s') % ', '.join(created)
               if created
               else _('All Direct Print actions already exist.'))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Direct Print'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def action_create_print_actions_silent(self):
        """Called from XML <function> on every install/upgrade."""
        try:
            created = self._ensure_print_actions()
            if created:
                _logger.info('Direct Print: created/repaired actions for %s', ', '.join(created))
        except Exception as e:
            _logger.warning('Direct Print: could not create actions: %s', e)
