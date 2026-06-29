# -*- coding: utf-8 -*-

from odoo import fields, models


class HmsAppointment(models.Model):
    _inherit = 'hms.appointment'

    card_commission_id = fields.Many2one(
        'res.card.commission',
        string='Card #',
        domain="[('state', '=', 'confirmed')]",
        copy=False,
    )
