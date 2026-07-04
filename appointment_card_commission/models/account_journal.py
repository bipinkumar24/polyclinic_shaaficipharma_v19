# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_appointment_commission_journal = fields.Boolean(
        string="Appointment Commission Journal",
        help="Invoices created from the appointment invoicing wizard with a "
             "Card # selected are posted to this journal.",
    )
