# -*- coding: utf-8 -*-
from odoo import fields, models


class AcsCommission(models.Model):
    _inherit = "acs.commission"

    remote_server_id = fields.Many2one(
        "product.remote.server",
        string="Remote Server",
        readonly=True,
        copy=False,
        index=True,
        help="Remote server this commission record was synchronized from.",
    )
    remote_id = fields.Integer(
        string="Remote ID",
        readonly=True,
        copy=False,
        index=True,
        help="Id of the matching acs.commission on the remote server.",
    )
