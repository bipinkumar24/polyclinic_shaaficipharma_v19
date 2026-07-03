# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    remote_server_id = fields.Many2one(
        "product.remote.server",
        string="Remote Server",
        readonly=True,
        copy=False,
        index=True,
        help="Remote server this partner was synchronized from.",
    )
    remote_id = fields.Integer(
        string="Remote ID",
        readonly=True,
        copy=False,
        index=True,
        help="Id of the matching res.partner on the remote server.",
    )
