# -*- coding: utf-8 -*-
from odoo import fields, models


class HmsPatient(models.Model):
    _inherit = "hms.patient"

    remote_server_id = fields.Many2one(
        "product.remote.server",
        string="Remote Server",
        readonly=True,
        copy=False,
        index=True,
        help="Remote server this patient was synchronized from.",
    )
    remote_id = fields.Integer(
        string="Remote ID",
        readonly=True,
        copy=False,
        index=True,
        help="Id of the matching hms.patient on the remote server.",
    )
