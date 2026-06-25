from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.depends('payment_type', 'company_id', 'can_edit_wizard', 'line_ids')
    def _compute_available_journal_ids(self):
        super()._compute_available_journal_ids()
        for wizard in self:
            if wizard.line_ids.move_id.filtered('patient_id'):
                wizard.available_journal_ids = wizard.available_journal_ids.filtered(
                    lambda journal: journal.is_cashier_receipts
                )
