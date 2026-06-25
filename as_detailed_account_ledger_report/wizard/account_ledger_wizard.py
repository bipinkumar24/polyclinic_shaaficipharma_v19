from odoo import models, fields, api


class AccountLedgerWizard(models.TransientModel):
    _name = 'account.ledger.wizard'
    _description = 'Account Ledger Report Wizard'

    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    # ==========================================================
    # Optional filter fields for Partner and Product
    # ==========================================================
    partner_id = fields.Many2one('res.partner', string='Partner')
    product_id = fields.Many2one('product.product', string='Product')
    company_id = fields.Many2one( 'res.company',  string='Company',
        required=True, default=lambda self: self.env.company
    )
    doc_status = fields.Selection(
        [('posted', 'Posted'), ('draft', 'Draft')], string='Doc Status', default='posted'
    )

    output_format = fields.Selection(
        [('html', 'HTML'), ('pdf', 'PDF'), ('xlsx', 'Excel')],
        string='Output Format', required=True, default='html'
    )

    def generate_report(self):
        """
        SIMPLIFIED: This version relies only on the standard docids mechanism,
        which is more robust against interference from other modules.
        """
        self.ensure_one()

        if self.output_format in ('html', 'pdf'):
            report_action_ref = f'as_detailed_account_ledger_report.action_report_detailed_account_ledger_{self.output_format}'
            return self.env.ref(report_action_ref).report_action(self)

        elif self.output_format == 'xlsx':
            data = {'wizard_id': self.id}
            return {
                'type': 'ir.actions.act_url',
                'url': f"/reports/xlsx/account_ledger?data={str(data)}",
                'target': 'new',
            }