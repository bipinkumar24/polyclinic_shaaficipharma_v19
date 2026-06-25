# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pulse_hours_per_physician = fields.Float(
        string="Open hours / physician / day", default=8.0,
        config_parameter="shafic_pulse.hours_per_physician")
    pulse_target_util = fields.Float(
        string="Chair utilization target (%)", default=75.0,
        config_parameter="shafic_pulse.target_util")
    pulse_cash_tolerance = fields.Float(
        string="Cash variance tolerance", default=10.0,
        config_parameter="shafic_pulse.cash_tolerance")
    pulse_aclass_count = fields.Integer(
        string="A-class top-seller count", default=40,
        config_parameter="shafic_pulse.aclass_count")
    pulse_expiry_days_near = fields.Integer(
        string="Near-expiry window (days)", default=30,
        config_parameter="shafic_pulse.expiry_days_near")
    pulse_expiry_days_window = fields.Integer(
        string="Expiry horizon (days)", default=90,
        config_parameter="shafic_pulse.expiry_days_window")
    pulse_deadstock_days = fields.Integer(
        string="Dead-stock threshold (days)", default=90,
        config_parameter="shafic_pulse.deadstock_days")
    pulse_appt_target = fields.Float(
        string="Appointment completion target (%)", default=80.0,
        config_parameter="shafic_pulse.appt_target")
