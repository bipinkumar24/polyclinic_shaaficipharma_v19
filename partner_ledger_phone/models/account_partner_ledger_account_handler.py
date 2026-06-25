from odoo import models

from collections import defaultdict

class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        aml_values = super()._get_aml_values(options, partner_ids, offset, limit)
        # Debug: Check if we're getting any data
        if partner_ids:
            partners = self.env['res.partner'].browse([pid for pid in partner_ids if pid])
            phone_mapping = {p.id: p.phone or '' for p in partners}
            for partner_id, amls in aml_values.items():
                for aml in amls:
                    aml['partner_phone'] = phone_mapping.get(partner_id, '')

        # Debug: Check modified data
        print("AML Values After:", aml_values)
        return aml_values

    def _build_partner_lines(self, report, options, level_shift=0):
        lines = []

        totals_by_column_group = {
            column_group_key: {
                total: 0.0
                for total in ['debit', 'credit', 'amount', 'balance','partner_phone']
            }
            for column_group_key in options['column_groups']
        }

        partners_results = self._query_partners(report, options)

        search_filter = options.get('filter_search_bar', '')
        accept_unknown_in_filter = search_filter.lower() in self._get_no_partner_line_label().lower()
        for partner, results in partners_results:
            if options['export_mode'] == 'print' and search_filter and not partner and not accept_unknown_in_filter:
                # When printing and searching for a specific partner, make it so we only show its lines, not the 'Unknown Partner' one, that would be
                # shown in case a misc entry with no partner was reconciled with one of the target partner's entries.
                continue

            partner_values = defaultdict(dict)
            for column_group_key in options['column_groups']:
                partner_sum = results.get(column_group_key, {})
                partner_values[column_group_key]['debit'] = partner_sum.get('debit', 0.0)
                partner_values[column_group_key]['credit'] = partner_sum.get('credit', 0.0)
                partner_values[column_group_key]['amount'] = partner_sum.get('amount', 0.0)
                partner_values[column_group_key]['balance'] = partner_sum.get('balance', 0.0)
                partner_values[column_group_key]['partner_phone'] = partner.phone if partner else 0
                totals_by_column_group[column_group_key]['debit'] += partner_values[column_group_key]['debit']
                totals_by_column_group[column_group_key]['credit'] += partner_values[column_group_key]['credit']
                totals_by_column_group[column_group_key]['amount'] += partner_values[column_group_key]['amount']
                totals_by_column_group[column_group_key]['balance'] += partner_values[column_group_key]['balance']
                # totals_by_column_group[column_group_key]['partner_phone'] = partner.phone

            lines.append(self._get_report_line_partners(options, partner, partner_values, level_shift=level_shift))

        return lines, totals_by_column_group