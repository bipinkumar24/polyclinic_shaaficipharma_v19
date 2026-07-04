# -*- coding: utf-8 -*-
from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    remote_server_id = fields.Many2one(
        "product.remote.server",
        string="Remote Server",
        readonly=True,
        copy=False,
        index=True,
        help="Remote server this department was synchronized from.",
    )
    remote_id = fields.Integer(
        string="Remote ID",
        readonly=True,
        copy=False,
        index=True,
        help="Id of the matching hr.department on the remote server.",
    )
