from odoo import models,fields, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id', store=True, readonly=False, precompute=True,
        check_company=True,
        index=False,  # covered by account_payment_journal_id_company_id_idx
        required=True,
        default=False,
    )

    @api.depends('payment_type', 'company_id')
    def _compute_available_journal_ids(self):
        super()._compute_available_journal_ids()
        is_cashier_action = self.env.context.get('default_is_cashier_action')
        if is_cashier_action:
            for pay in self:
                pay.available_journal_ids = pay.available_journal_ids.filtered(
                    lambda j: j.is_cashier_receipts
                )
