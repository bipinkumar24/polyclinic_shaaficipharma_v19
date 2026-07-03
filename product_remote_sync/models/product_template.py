# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    remote_server_id = fields.Many2one(
        "product.remote.server",
        string="Remote Server",
        readonly=True,
        copy=False,
        index=True,
        help="Remote server this product was synchronized from.",
    )
    remote_id = fields.Integer(
        string="Remote ID",
        readonly=True,
        copy=False,
        index=True,
        help="Id of the matching product.template on the remote server.",
    )
