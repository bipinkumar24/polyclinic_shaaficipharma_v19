# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PharmacyStockValueDaily(models.Model):
    """One row per day per company recording total inventory value.

    Used as the denominator for the expiry write-off rate so the rate is
    computed against a true period average rather than a single-day
    snapshot. Populated by the daily cron and queried by the bonus
    scorecard when it needs the average for a month.
    """
    _name = 'pharmacy.stock.value.daily'
    _description = 'Pharmacy Daily Stock Value Snapshot'
    _order = 'capture_date desc, company_id'
    _rec_name = 'capture_date'

    capture_date = fields.Date(string='Date', required=True, index=True,
                               default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 required=True, index=True)
    stock_value = fields.Float(string='Total Stock Value', readonly=True,
                               digits=(16, 2))
    year = fields.Integer(string='Year', compute='_compute_year_month',
                          store=True, index=True)
    month = fields.Integer(string='Month', compute='_compute_year_month',
                           store=True, index=True)

    _sql_constraints = [
        ('uniq_date_company',
         'unique(capture_date, company_id)',
         'Only one stock value snapshot per day and company.'),
    ]

    @api.depends('capture_date')
    def _compute_year_month(self):
        for rec in self:
            if rec.capture_date:
                rec.year = rec.capture_date.year
                rec.month = rec.capture_date.month
            else:
                rec.year = 0
                rec.month = 0
