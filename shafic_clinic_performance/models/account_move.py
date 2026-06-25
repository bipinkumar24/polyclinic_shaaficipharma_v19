# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ACS HMS core stores only ``ref_physician_id`` (the *referring* physician,
    # a res.partner). The treating/performing physician lives on the source
    # clinical document and is never copied to the posted invoice. We add it
    # here so it can be reported on, and auto-fill it from whichever clinical
    # record is linked to the invoice. It stays editable so a cashier can tag
    # lab-only or radiology-only invoices by hand.
    physician_id = fields.Many2one(
        'hms.physician',
        string='Physician',
        index=True,
        tracking=True,
        compute='_compute_shafic_physician_id',
        store=True,
        readonly=False,
        help="Treating / performing physician for this patient invoice. "
             "Auto-filled from the linked appointment, procedure, surgery or "
             "vaccination; you can override it (e.g. for lab-only or "
             "radiology-only invoices).")

    # Reverse links from the source documents. The inverse ``invoice_id`` field
    # is confirmed to exist on each of these models in the installed suite
    # (acs_hms / acs_hms_surgery / acs_hms_vaccination), all guaranteed present
    # via the acs_hms_cashier dependency.
    shafic_appointment_ids = fields.One2many(
        'hms.appointment', 'invoice_id', string='Linked Appointments')
    shafic_surgery_ids = fields.One2many(
        'hms.surgery', 'invoice_id', string='Linked Surgeries')
    shafic_procedure_ids = fields.One2many(
        'acs.patient.procedure', 'invoice_id', string='Linked Procedures')
    shafic_vaccination_ids = fields.One2many(
        'acs.vaccination', 'invoice_id', string='Linked Vaccinations')

    @api.depends(
        'appointment_id',
        'procedure_id',
        'shafic_appointment_ids',
        'shafic_surgery_ids',
        'shafic_procedure_ids',
        'shafic_vaccination_ids',
    )
    def _compute_shafic_physician_id(self):
        """Resolve the treating physician from the linked clinical record.

        Priority:
          1. The direct ``appointment_id`` / ``procedure_id`` links that ACS
             core already places on the invoice.
          2. The reverse ``invoice_id`` links from appointment / surgery /
             procedure / vaccination documents.
        If no clinical source is found, any manually entered physician is kept
        (so lab-only / radiology-only invoices tagged by hand are preserved).
        """
        for move in self:
            physician = False

            # 1) Direct links ACS core puts on the invoice itself.
            appointment = move.appointment_id
            if appointment and 'physician_id' in appointment._fields:
                physician = appointment.physician_id
            if not physician:
                procedure = move.procedure_id
                if procedure and 'physician_id' in procedure._fields:
                    physician = procedure.physician_id

            # 2) Reverse links from the source documents (first match wins).
            if not physician:
                for records in (
                    move.shafic_appointment_ids,
                    move.shafic_surgery_ids,
                    move.shafic_procedure_ids,
                    move.shafic_vaccination_ids,
                ):
                    record = records[:1]
                    if record and 'physician_id' in record._fields \
                            and record.physician_id:
                        physician = record.physician_id
                        break

            if physician:
                move.physician_id = physician
            elif not move.physician_id:
                move.physician_id = False
