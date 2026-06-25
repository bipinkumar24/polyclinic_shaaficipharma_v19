# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HmsAppointment(models.Model):
    _inherit = 'hms.appointment'

    @api.onchange('purpose_id', 'date')
    def _onchange_dental_purpose_duration(self):
        """When a visit type with a default duration is chosen, size the
        appointment automatically (end time = start + duration)."""
        purpose = self.purpose_id
        if purpose and purpose.default_duration and self.date:
            self.manual_planned_duration = purpose.default_duration
            self.date_to = self.date + timedelta(
                hours=purpose.default_duration)

    @api.constrains('date', 'date_to', 'physician_id', 'cabin_id',
                    'state', 'department_type')
    def _check_dental_double_booking(self):
        """A dental appointment may not overlap another (non-cancelled)
        appointment on the same dentist or the same chair. Scoped to dental
        appointments so existing general/nurse flows are untouched, and can
        be switched off per company."""
        for rec in self:
            if rec.state == 'cancel' or rec.department_type != 'dental':
                continue
            if not rec.company_id.dental_block_double_booking:
                continue
            if not (rec.date and rec.date_to) or rec.date_to <= rec.date:
                continue

            overlap = [
                ('id', '!=', rec.id),
                ('state', '!=', 'cancel'),
                ('date', '<', rec.date_to),
                ('date_to', '>', rec.date),
            ]
            if rec.company_id:
                overlap.append(('company_id', '=', rec.company_id.id))

            if rec.physician_id:
                clash = self.search(
                    overlap + [('physician_id', '=', rec.physician_id.id)],
                    limit=1)
                if clash:
                    raise ValidationError(_(
                        "Double booking: Dr. %(doc)s already has appointment "
                        "%(ref)s in this time slot.",
                        doc=rec.physician_id.name,
                        ref=clash.display_name))

            if rec.cabin_id:
                clash = self.search(
                    overlap + [('cabin_id', '=', rec.cabin_id.id)], limit=1)
                if clash:
                    raise ValidationError(_(
                        "Double booking: chair %(chair)s is already taken by "
                        "%(ref)s in this time slot.",
                        chair=rec.cabin_id.name,
                        ref=clash.display_name))
