from odoo import api, models


class ReportPosSessionClosingSummary(models.AbstractModel):
    _name = 'report.pos_cashier_bonus.report_session_closing_summary'
    _description = 'POS Session Closing Summary'

    @api.model
    def _get_report_values(self, docids, data=None):
        sessions = self.env['pos.session'].browse(docids)
        groups = []
        for config in sessions.mapped('config_id'):
            subset = sessions.filtered(lambda s: s.config_id == config)
            groups.append({
                'register': config.display_name or '',
                'journal': subset[:1].closing_journal_id.display_name or '',
                'count': len(subset),
                'gain': sum(subset.mapped('cash_gain_amount')),
                'loss': sum(subset.mapped('cash_loss_amount')),
                'difference': sum(subset.mapped('cash_difference_amount')),
            })
        no_config = sessions.filtered(lambda s: not s.config_id)
        if no_config:
            groups.append({
                'register': 'Unassigned',
                'journal': '',
                'count': len(no_config),
                'gain': sum(no_config.mapped('cash_gain_amount')),
                'loss': sum(no_config.mapped('cash_loss_amount')),
                'difference': sum(no_config.mapped('cash_difference_amount')),
            })
        groups.sort(key=lambda g: g['register'])
        return {
            'doc_ids': docids,
            'doc_model': 'pos.session',
            'docs': sessions,
            'groups': groups,
            'currency': sessions[:1].currency_id or self.env.company.currency_id,
            'company': sessions[:1].company_id or self.env.company,
            'total_count': len(sessions),
            'total_gain': sum(sessions.mapped('cash_gain_amount')),
            'total_loss': sum(sessions.mapped('cash_loss_amount')),
            'total_difference': sum(sessions.mapped('cash_difference_amount')),
        }
