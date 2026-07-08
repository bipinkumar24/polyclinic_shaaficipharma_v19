# -*- coding: utf-8 -*-
from odoo import fields, models


class RadiologyRequest(models.Model):
    _inherit = "acs.radiology.request"

    remote_server_id = fields.Many2one(
        "product.remote.server", string="Remote Server", readonly=True,
        copy=False, index=True,
    )
    remote_id = fields.Integer(
        string="Remote ID", readonly=True, copy=False, index=True,
    )
    x_v18_name = fields.Char(
        string="V18 Request Number", readonly=True, copy=False, index=True,
        help="The 'name' (Request Number) of the corresponding record on the "
        "Odoo 18 server. The local name is generated automatically; this field "
        "keeps the remote value and is used to identify and link records across "
        "versions and to prevent duplicate creation during synchronization.",
    )


class PatientRadiologyTest(models.Model):
    _inherit = "patient.radiology.test"

    remote_server_id = fields.Many2one(
        "product.remote.server", string="Remote Server", readonly=True,
        copy=False, index=True,
    )
    remote_id = fields.Integer(
        string="Remote ID", readonly=True, copy=False, index=True,
    )
    x_v18_name = fields.Char(
        string="V18 Test ID", readonly=True, copy=False, index=True,
        help="The 'name' (Test ID) of the corresponding record on the Odoo 18 "
        "server. Used to identify and link records across versions.",
    )
