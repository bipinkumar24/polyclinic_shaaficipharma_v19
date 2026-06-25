# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PharmacyCostAnomalySnapshot(models.Model):
    """Daily history of cost/price anomalies.

    The live report (report.pharmacy.cost.price.anomaly) is computed from
    current state and has no notion of time — it always shows "what is
    wrong right now". That can't answer "what broke today" or "show me
    last week's anomalies".

    This model stores a dated copy each day (written by the daily cron),
    so the team can:
      - Filter anomalies by date / date range
      - See which anomalies are NEW today (weren't flagged the previous
        snapshot) via the is_new flag and the "New Today" filter

    It is a plain stored model (not a SQL view) because it accumulates
    history. A retention cleanup keeps it bounded.
    """
    _name = 'pharmacy.cost.anomaly.snapshot'
    _description = 'Cost / Price Anomaly Snapshot'
    _order = 'snapshot_date desc, severity_rank, product_id'

    snapshot_date = fields.Date(
        string='Date', required=True, index=True)
    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
        ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template')
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category')
    company_id = fields.Many2one('res.company', string='Company', index=True)

    severity = fields.Selection(
        selection=[
            ('critical', 'Critical'),
            ('warning', 'Warning'),
            ('review', 'Review'),
        ], string='Severity')
    severity_rank = fields.Integer(string='Severity Rank')

    flag_below_cost = fields.Boolean(string='Below Cost')
    flag_thin_margin = fields.Boolean(string='Thin Margin')
    flag_cost_spike = fields.Boolean(string='Cost Spike')
    flag_peer_outlier = fields.Boolean(string='Peer Outlier')

    current_cost = fields.Float(string='Effective Cost', digits=(12, 4))
    standard_cost = fields.Float(string='Standard Cost', digits=(12, 4))
    current_price = fields.Float(string='Price', digits=(12, 2))
    margin_pct = fields.Float(string='Margin %', digits=(8, 2))
    cost_variance_pct = fields.Float(string='Cost Variance %', digits=(8, 2))
    cost_source = fields.Selection(
        selection=[
            ('warehouse', 'Warehouse-Wise'),
            ('standard', 'Standard (Fallback)'),
            ('zero', 'No Data'),
        ], string='Cost Source')

    is_new = fields.Boolean(
        string='New', index=True,
        help='This product was flagged in this snapshot but was not '
             'flagged in the previous snapshot — i.e. the anomaly is new.')

    def action_open_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': self.product_tmpl_id.id,
            'view_mode': 'form',
        }

    @api.model
    def capture_snapshot(self, company=None):
        """Write today's snapshot of the live anomaly report.

        Idempotent for a given (date, company): existing rows for today
        are deleted first, so re-running the cron the same day refreshes
        rather than duplicates.

        is_new is computed against the most recent PRIOR snapshot date
        for the same company.
        """
        companies = company or self.env['res.company'].search([])
        today = fields.Date.context_today(self)
        Live = self.env['report.pharmacy.cost.price.anomaly']

        for comp in companies:
            # Clear today's existing rows for idempotency.
            self.search([
                ('snapshot_date', '=', today),
                ('company_id', '=', comp.id),
            ]).unlink()

            # Previous snapshot date (for is_new comparison).
            prev = self.search([
                ('snapshot_date', '<', today),
                ('company_id', '=', comp.id),
            ], order='snapshot_date desc', limit=1)
            prev_product_ids = set()
            if prev:
                prev_rows = self.search([
                    ('snapshot_date', '=', prev.snapshot_date),
                    ('company_id', '=', comp.id),
                ])
                prev_product_ids = set(prev_rows.mapped('product_id').ids)

            # Read the live report for this company.
            live_rows = Live.with_company(comp).search([
                ('company_id', '=', comp.id),
            ])

            vals_list = []
            for r in live_rows:
                vals_list.append({
                    'snapshot_date': today,
                    'product_id': r.product_id.id,
                    'product_tmpl_id': r.product_tmpl_id.id,
                    'pharmacy_category_id': r.pharmacy_category_id.id,
                    'company_id': comp.id,
                    'severity': r.severity,
                    'severity_rank': r.severity_rank,
                    'flag_below_cost': r.flag_below_cost,
                    'flag_thin_margin': r.flag_thin_margin,
                    'flag_cost_spike': r.flag_cost_spike,
                    'flag_peer_outlier': r.flag_peer_outlier,
                    'current_cost': r.current_cost,
                    'standard_cost': r.standard_cost,
                    'current_price': r.current_price,
                    'margin_pct': r.margin_pct,
                    'cost_variance_pct': r.cost_variance_pct,
                    'cost_source': r.cost_source,
                    'is_new': r.product_id.id not in prev_product_ids,
                })
            if vals_list:
                self.create(vals_list)
        return True

    @api.model
    def cleanup_old_snapshots(self, keep_days=180):
        """Delete snapshots older than keep_days to keep the table bounded."""
        from datetime import timedelta
        cutoff = fields.Date.context_today(self) - timedelta(days=keep_days)
        old = self.search([('snapshot_date', '<', cutoff)])
        old.unlink()
        return True
