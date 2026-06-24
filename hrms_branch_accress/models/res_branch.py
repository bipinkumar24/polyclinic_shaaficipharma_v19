# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResBranch(models.Model):
    _name = 'res.branch'
    _inherit = ['res.branch','pos.load.mixin']

