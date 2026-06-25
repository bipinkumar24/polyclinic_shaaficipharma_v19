# -*- coding: utf-8 -*-
from odoo import fields, models


class AppointmentPurpose(models.Model):
    _inherit = 'appointment.purpose'

    default_duration = fields.Float(
        string='Default Duration (hours)', default=0.5,
        help='Used to auto-set the appointment end time when this visit '
             'type is chosen (e.g. 0.5 = 30 minutes).')
