# -*- coding: utf-8 -*-
from odoo import fields, models


class HmsPhysician(models.Model):
    _inherit = "hms.physician"

    remote_server_id = fields.Many2one(
        "product.remote.server",
        string="Remote Server",
        readonly=True,
        copy=False,
        index=True,
        help="Remote server this physician was synchronized from.",
    )
    remote_id = fields.Integer(
        string="Remote ID",
        readonly=True,
        copy=False,
        index=True,
        help="Id of the matching hms.physician on the remote server.",
    )
