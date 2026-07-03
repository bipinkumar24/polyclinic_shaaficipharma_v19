# -*- coding: utf-8 -*-
from odoo import fields, models


class ResBranch(models.Model):
    _inherit = "res.branch"

    remote_server_id = fields.Many2one(
        "product.remote.server", string="Remote Server", readonly=True,
        copy=False, index=True,
    )
    remote_id = fields.Integer(
        string="Remote ID", readonly=True, copy=False, index=True,
    )
