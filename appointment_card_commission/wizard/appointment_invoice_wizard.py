# -*- coding: utf-8 -*-

from odoo import fields, models


class AppointmentInvoiceWizard(models.TransientModel):
    _inherit = 'appointment.invoice.wizard'

    card_commission_id = fields.Many2one(
        'res.card.commission',
        string='Card #',
        domain="[('state', '=', 'confirmed')]",
        default=lambda self: self._default_card_commission_id(),
    )

    def _default_card_commission_id(self):
        appointment_id = self.env.context.get('default_appointment_id')
        if appointment_id:
            appointment = self.env['hms.appointment'].browse(appointment_id)
            return appointment.card_commission_id.id
        return False

    def action_create_invoice(self):
        res = super().action_create_invoice()
        invoice = self.appointment_id.invoice_id
        if self.card_commission_id and invoice:
            invoice.card_commission_id = self.card_commission_id.id
        if invoice:
            journal = self.env['account.journal'].search([('name', '=', 'Clinic Customer')], limit=1)
            if journal:
                invoice.journal_id = journal.id
        return res
