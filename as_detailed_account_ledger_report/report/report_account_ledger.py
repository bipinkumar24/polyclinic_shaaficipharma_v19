import logging
from odoo import models, api, fields
from odoo.exceptions import UserError
from collections import defaultdict
from datetime import datetime

_logger = logging.getLogger(__name__)


class ReportAccountLedger(models.AbstractModel):
    _name = 'report.as_detailed_account_ledger_report.report_ledger_template'
    _description = 'Detailed Account Ledger Report Data'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("--- Starting _get_report_values for Detailed Ledger ---")

        wizard = self.env['account.ledger.wizard'].browse(docids[0])
        account = wizard.account_id
        date_from = wizard.date_from
        date_to = wizard.date_to
        company = wizard.company_id

        if not account:
            raise UserError("A valid account was not found in the wizard.")

        _logger.info(
            f"Report parameters: Account={account.code}, Type={account.internal_group}, From={date_from}, To={date_to}")

        # --- MODIFICATION FOR BALANCE CALCULATION ---
        # Get all posted move lines for the account
        """
        all_lines = self.env['account.move.line'].search([
            ('account_id', '=', account.id),
            ('move_id.state', '=', 'posted')
        ], order='date, id')
        """

        # 1. Start with the base, required filters
        base_domain = [
            ('account_id', '=', account.id),
            ('company_id', '=', company.id)
        ]

        # 2. Conditionally add optional filters if they have been set
        if wizard.partner_id:
            base_domain.append(('partner_id', '=', wizard.partner_id.id))
            _logger.info(f"Report Filter Applied: Partner ID {wizard.partner_id.id}")

        if wizard.product_id:
            base_domain.append(('product_id', '=', wizard.product_id.id))
            _logger.info(f"Report Filter Applied: Product ID {wizard.product_id.id}")

        if wizard.doc_status:
            base_domain.append(('move_id.state', '=', wizard.doc_status))
            _logger.info(f"Report Filter Applied: doc_status {wizard.doc_status}")


        # 3. Perform the search using the final, complete domain
        all_lines = self.env['account.move.line'].search(base_domain, order='date, id')

        # Filter lines for opening balance calculation
        opening_lines = all_lines.filtered(lambda l: l.date < date_from)

        # Filter lines for the report's period
        report_lines = all_lines.filtered(lambda l: date_from <= l.date <= date_to)
        final_line = report_lines

        if account.account_type == 'asset_receivable':
            new_lines = self.env['account.move.line']

            for line in report_lines:
                move = line.move_id


                # If Customer Invoice → keep line
                if move.move_type == 'out_invoice':
                    other_lines = move.invoice_line_ids.filtered(
                        lambda l: l.id != line.id
                    )
                    new_lines |= other_lines

                # # Other entries → keep normal
                else:
                    new_lines |= line

            report_lines = new_lines

        if account.account_type == 'liability_payable':
            new_lines = self.env['account.move.line']

            for line in report_lines:
                move = line.move_id

                # If Vendor Bill → remove current line & take other move lines
                if move.move_type == 'in_invoice':
                    other_lines = move.invoice_line_ids.filtered(
                        lambda l: l.id != line.id
                    )
                    new_lines |= other_lines

                else:
                    new_lines |= line

            report_lines = new_lines

        # Calculate raw balance (Debit - Credit)
        opening_balance_raw = sum(opening_lines.mapped('balance'))
        report_period_balance_raw = sum(final_line.mapped('balance'))

        # Conditionally adjust the balance based on account type
        # For Asset and Expense, Debit is positive. For others, Credit is positive.
        if account.internal_group in ('asset', 'expense'):
            opening_balance = opening_balance_raw
            closing_balance = opening_balance + report_period_balance_raw
        else:  # For Liability, Equity, Income
            opening_balance = -opening_balance_raw
            closing_balance = opening_balance - report_period_balance_raw

        _logger.info(f"Opening Balance (Raw): {opening_balance_raw}, Final: {opening_balance}")
        _logger.info(f"Closing Balance Final: {closing_balance}")

        # Group lines for the report body
        lines_by_date = defaultdict(list)
        for line in report_lines:
            lines_by_date[line.date].append(line)

        report_data = {
            'doc_ids': docids,
            'doc_model': 'account.ledger.wizard',
            'docs': wizard,
            'account': account,
            'company': company,
            'date_from': date_from.strftime('%d/%m/%Y'),
            'date_to': date_to.strftime('%d/%m/%Y'),
            'date_printed': datetime.now().strftime('%d/%m/%Y %I:%M %p'),
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'lines_by_date': dict(lines_by_date),
            'sorted_dates': sorted(lines_by_date.keys()),
            'get_status_label': lambda state: 'Posted' if state == 'posted' else 'Draft',
        }

        _logger.info("Report data prepared successfully. Returning values to QWeb.")
        return report_data
