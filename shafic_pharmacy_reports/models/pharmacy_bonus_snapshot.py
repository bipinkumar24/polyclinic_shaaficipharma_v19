# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PharmacyBonusSnapshot(models.Model):
    """Stored monthly snapshot of the inventory bonus scorecard.

    The scorecard model itself reads live inventory state. To pay the
    bonus honestly for a closed month we need a record of what the
    figures actually were at that month's end; this model stores that.

    A single record per (year, month, company) is enforced by SQL
    constraint. Records are created by the monthly cron and can also be
    captured manually for back-filling.
    """
    _name = 'pharmacy.bonus.snapshot'
    _description = 'Pharmacy Inventory Bonus Snapshot'
    _order = 'year desc, month desc'
    _rec_name = 'display_name'

    display_name = fields.Char(string='Period', compute='_compute_display_name',
                               store=True)
    year = fields.Integer(string='Year', required=True, index=True)
    month = fields.Integer(string='Month', required=True, index=True)
    capture_date = fields.Date(string='Captured On', required=True,
                               default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 required=True, index=True)

    # KPI raw figures
    average_stock_value = fields.Float(string='Average Stock Value',
                                       readonly=True)
    expired_value = fields.Float(string='Expired Value', readonly=True)
    near_expiry_value = fields.Float(string='Near-Expiry Value',
                                     readonly=True)

    # KPI computed rates
    expiry_rate = fields.Float(string='Expiry Write-off Rate (%)',
                               readonly=True, digits=(8, 2))
    catch_pct = fields.Float(string='Near-Expiry Caught (%)',
                             readonly=True, digits=(8, 2))
    data_pct = fields.Float(string='Data Completeness (%)',
                            readonly=True, digits=(8, 2))

    # KPI scores (0-100) and payouts ($)
    expiry_score = fields.Float(string='Expiry Score (%)', readonly=True,
                                digits=(8, 1))
    catch_score = fields.Float(string='Catch Score (%)', readonly=True,
                               digits=(8, 1))
    data_score = fields.Float(string='Data Score (%)', readonly=True,
                              digits=(8, 1))
    expiry_pay = fields.Float(string='Expiry Earned ($)', readonly=True)
    catch_pay = fields.Float(string='Catch Earned ($)', readonly=True)
    data_pay = fields.Float(string='Data Earned ($)', readonly=True)
    total_earned = fields.Float(string='Total Team Pool Earned ($)',
                                readonly=True)
    total_possible = fields.Float(string='Total Possible ($)', readonly=True)
    exclusion_total = fields.Float(
        string='Approved Exclusions ($)', readonly=True,
        help='Total uncontrollable losses that were excluded from the '
             'expiry rate denominator for this period.')

    _sql_constraints = [
        ('uniq_period_company',
         'unique(year, month, company_id)',
         'Only one bonus snapshot per month and company.'),
    ]

    _MONTH_NAMES = [
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December',
    ]

    @api.depends('year', 'month')
    def _compute_display_name(self):
        for snap in self:
            if 1 <= (snap.month or 0) <= 12:
                snap.display_name = '%s %s' % (
                    self._MONTH_NAMES[snap.month], snap.year)
            else:
                snap.display_name = '%s/%s' % (snap.month or '', snap.year or '')

    def action_recapture(self):
        """Re-run the scorecard for this snapshot's period and overwrite
        the stored figures. Useful when the period is the current month
        and the team wants to refresh mid-month."""
        for snap in self:
            self.env['pharmacy.bonus.scorecard'].capture_month_snapshot(
                snap.year, snap.month, snap.company_id.id, replace=True)
        return True
