# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    collection_sms_exclude = fields.Boolean(
        string='Exclude from Collection SMS',
        help="If ticked, this contact is never included in debt-collection SMS "
             "batches (e.g. employees, staff, do-not-contact customers). The "
             "company's own branches are always excluded automatically.",
    )
