# -*- coding: utf-8 -*-
from odoo import fields, models


class PatientLaboratoryTest(models.Model):
    _inherit = "patient.laboratory.test"

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
        "server. Used to identify and link records across versions and to "
        "prevent duplicate creation during synchronization.",
    )
