# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.fields import Domain


class AccountMove(models.Model):
    _inherit = "account.move"
    
    @api.model
    def acs_action_cash_payment(self, payment_journal=False):
        PaymentReg = self.env['account.payment.register']
        if not payment_journal:
            payment_journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        for inv in self:
            if inv.state=='draft':
                inv.action_post()
            payment = PaymentReg.with_context(active_model='account.move',active_ids=[inv.id]).create({
                'journal_id': payment_journal.id,
            })
            payment._create_payments()

    is_patient = fields.Boolean(
        string="Is Patient",
        related='partner_id.is_patient',
        store=True,
        index=True
    )

    # def search(self, args, **kwargs):
    #     print("wwwwwwwwwwwwwwwwww")
    #     if self.env.context.get('patient_invoice'):
    #         print("wwwwwwwwwwwwwwwww")
    #         patient_partner_ids = self.env['hms.patient'].search([]).mapped('partner_id').ids
    #         args += [('partner_id', 'in', patient_partner_ids)]

    #     return super(AccountMove, self).search(args, **kwargs)

    # @api.model
    # def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):

    #     if self.env.context.get('patient_invoice'):
    #         # Get all partner_ids which are patients
    #         patient_partner_ids = self.env['hms.patient'].search([]).mapped('partner_id').ids

    #         # Safety check
    #         if patient_partner_ids:
    #             patient_domain = [
    #                 ('partner_id', 'in', patient_partner_ids),
    #                 ('move_type', '=', 'out_invoice'),
    #             ]
    #         else:
    #             # No patients → no invoices
    #             patient_domain = [('id', '=', 0)]

    #         domain = Domain.AND([domain, patient_domain])

    #     return super()._search(
    #         domain,
    #         offset=offset,
    #         limit=limit,
    #         order=order,
    #         access_rights_uid=access_rights_uid
    #     )

    @api.model
    def _search(self, domain, *args, **kwargs):
        """
        Context-based filter to show only Patient Invoices.

        When context key `patient_invoice` is set,
        only invoices whose partner exists in `hms.patient.partner_id`
        will be returned.
        """
        if self.env.context.get('patient_invoice'):
            # Fetch partner_ids linked with patients
            patient_partner_ids = self.env['hms.patient'].search([]).mapped('partner_id').ids

            if patient_partner_ids:
                patient_domain = [
                    ('partner_id', 'in', patient_partner_ids),
                    ('move_type', '=', 'out_invoice'),
                ]
            else:
                # No patients found → return no records
                patient_domain = [('id', '=', 0)]

            domain = Domain.AND([domain, patient_domain])

        return super()._search(domain, *args, **kwargs)

