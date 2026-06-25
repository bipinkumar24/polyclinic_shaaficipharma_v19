# -*- coding: utf-8 -*-
from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    department_type = fields.Selection(
        selection_add=[('dental', 'Dental')],
        ondelete={'dental': 'set null'})
