# -*- coding: utf-8 -*-
from odoo import fields, models


class AppointmentCabin(models.Model):
    _inherit = 'appointment.cabin'

    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    notes = fields.Char(string='Notes')
