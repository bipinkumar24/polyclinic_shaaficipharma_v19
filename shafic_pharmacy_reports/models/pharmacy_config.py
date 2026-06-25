# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pharmacy_expiry_alert_days = fields.Integer(
        string='Expiry Alert Threshold (days)',
        config_parameter='shafic_pharmacy_reports.expiry_alert_days',
        default=90,
        help='Products expiring within this number of days trigger alerts.')
    pharmacy_dead_stock_days = fields.Integer(
        string='Dead Stock Threshold (days)',
        config_parameter='shafic_pharmacy_reports.dead_stock_days',
        default=180,
        help='Products with no sales within this period are flagged as '
             'dead stock.')
    pharmacy_slow_stock_days = fields.Integer(
        string='Slow Moving Threshold (days)',
        config_parameter='shafic_pharmacy_reports.slow_stock_days',
        default=60,
        help='Products with no sales within this period are flagged as '
             'slow moving.')
    pharmacy_velocity_slow_days_of_cover = fields.Float(
        string='Slow Velocity Threshold (days of cover)',
        config_parameter='shafic_pharmacy_reports.velocity_slow_days_of_cover',
        default=90.0,
        help='At the current sales rate, if on-hand stock would last '
             'more than this many days, the product is flagged as Slow '
             'Velocity. Independent from age — catches young products '
             'that are over-stocked relative to demand. Default 90 '
             'days (3 months of cover) is appropriate for pharmacy '
             'where products have shelf life.')
    pharmacy_velocity_dead_days_of_cover = fields.Float(
        string='Dead Velocity Threshold (days of cover)',
        config_parameter='shafic_pharmacy_reports.velocity_dead_days_of_cover',
        default=180.0,
        help='At the current sales rate, if on-hand stock would last '
             'more than this many days, the product is flagged as Dead '
             'Velocity. Default 180 days (6 months) — by this point a '
             'product is either over-ordered or genuinely not selling.')
    pharmacy_cost_warn_ratio = fields.Float(
        string='Cost Warning Ratio',
        config_parameter='shafic_pharmacy_reports.cost_warn_ratio',
        default=1.0,
        help='Warn when a product cost reaches this multiple of its '
             'sale price. 1.0 means warn as soon as cost >= price '
             '(the recommended setting — a healthy product always has '
             'cost below price). Raise it (e.g. 1.5) to tolerate '
             'thin-margin products without warning.')
    pharmacy_near_expiry_discount = fields.Float(
        string='Suggested Near-Expiry Discount (%)',
        config_parameter='shafic_pharmacy_reports.near_expiry_discount',
        default=20.0)
    pharmacy_expiry_notify_user_ids = fields.Many2many(
        'res.users', string='Expiry Alert Recipients',
        relation='pharmacy_config_expiry_user_rel',
        help='Users notified by the daily expiry scheduled job.')

    # --- Inventory bonus scheme ------------------------------------------
    pharmacy_bonus_pool = fields.Float(
        string='Monthly Team Bonus Pool',
        config_parameter='shafic_pharmacy_reports.bonus_pool',
        default=255.0,
        help='Total monthly team bonus pool shared by the inventory team.')
    pharmacy_bonus_expiry_target = fields.Float(
        string='Expiry Write-off Target (%)',
        config_parameter='shafic_pharmacy_reports.bonus_expiry_target',
        default=1.4,
        help='Expiry write-off rate (expired value / average stock value) '
             'at or below which the expiry KPI pays in full.')
    pharmacy_bonus_expiry_baseline = fields.Float(
        string='Expiry Write-off Baseline (%)',
        config_parameter='shafic_pharmacy_reports.bonus_expiry_baseline',
        default=2.0,
        help='Expiry write-off rate at or above which the expiry KPI pays '
             'nothing. Payout scales linearly between target and baseline.')
    pharmacy_bonus_catch_target = fields.Float(
        string='Near-Expiry Caught Target (%)',
        config_parameter='shafic_pharmacy_reports.bonus_catch_target',
        default=80.0,
        help='Percentage of near-expiry stock value cleared before expiry '
             'at or above which the catch KPI pays in full.')
    pharmacy_bonus_data_target = fields.Float(
        string='Data Completeness Target (%)',
        config_parameter='shafic_pharmacy_reports.bonus_data_target',
        default=98.0,
        help='Product data completeness (barcode, reference, lot) at or '
             'above which the data KPI pays in full.')
    pharmacy_bonus_data_floor = fields.Float(
        string='Data Completeness Floor (%)',
        config_parameter='shafic_pharmacy_reports.bonus_data_floor',
        default=90.0,
        help='Data completeness at or below which the data KPI pays '
             'nothing. Payout scales linearly up to the target.')
    pharmacy_bonus_weight_expiry = fields.Float(
        string='Expiry KPI Weight',
        config_parameter='shafic_pharmacy_reports.bonus_weight_expiry',
        default=115.0,
        help='Share of the team pool allocated to the expiry write-off KPI.')
    pharmacy_bonus_weight_catch = fields.Float(
        string='Near-Expiry Caught Weight',
        config_parameter='shafic_pharmacy_reports.bonus_weight_catch',
        default=50.0,
        help='Share of the team pool allocated to the near-expiry catch KPI.')
    pharmacy_bonus_weight_data = fields.Float(
        string='Data Completeness Weight',
        config_parameter='shafic_pharmacy_reports.bonus_weight_data',
        default=90.0,
        help='Share of the team pool allocated to the data completeness KPI.')

    # --- Receiving checklist enforcement ---------------------------------
    pharmacy_receiving_block = fields.Boolean(
        string='Block Receipts with Missing Data',
        config_parameter='shafic_pharmacy_reports.receiving_block',
        default=False,
        help='When enabled, goods receipts cannot be confirmed if any '
             'product is missing barcode, internal reference, expiry '
             'date or lot/batch (where required). Warn-only mode is '
             'used when this is off.')
    pharmacy_receiving_require_barcode = fields.Boolean(
        string='Require Barcode at Receiving',
        config_parameter='shafic_pharmacy_reports.receiving_require_barcode',
        default=True)
    pharmacy_receiving_require_ref = fields.Boolean(
        string='Require Internal Reference at Receiving',
        config_parameter='shafic_pharmacy_reports.receiving_require_ref',
        default=True)
    pharmacy_receiving_require_expiry = fields.Boolean(
        string='Require Expiry Date at Receiving',
        config_parameter='shafic_pharmacy_reports.receiving_require_expiry',
        default=True,
        help='For lot/serial-tracked products: each receipt line must '
             'have an expiration date set on its lot.')
    pharmacy_receiving_require_lot = fields.Boolean(
        string='Require Lot/Batch at Receiving',
        config_parameter='shafic_pharmacy_reports.receiving_require_lot',
        default=True,
        help='For lot/serial-tracked products: each move line must '
             'have a lot/serial selected or created.')

    # --- Auto-reorder preparation -------------------------------------
    pharmacy_auto_reorder_cap = fields.Float(
        string='Auto-Reorder Cap per Draft ($)',
        config_parameter='shafic_pharmacy_reports.auto_reorder_cap',
        default=1000.0,
        help='Maximum total cost of any single auto-prepared draft '
             'purchase order. If the calculated total exceeds this '
             'cap, no draft is created — an alert email is sent to '
             'the digest recipients instead so a person can split the '
             'order manually.')
    pharmacy_auto_reorder_velocity_pct = fields.Float(
        string='Auto-Reorder Velocity Threshold (%)',
        config_parameter='shafic_pharmacy_reports.auto_reorder_velocity_pct',
        default=20.0,
        help='What "hot" means: products in the top N% of '
             'trailing-90-day sales velocity qualify. 20% is the '
             'default — products that sell more than 80% of your '
             'priced range. Lower values are stricter (fewer hot '
             'products); higher values are looser.')
    pharmacy_auto_reorder_cover_days = fields.Float(
        string='Auto-Reorder Cover Threshold (Days)',
        config_parameter='shafic_pharmacy_reports.auto_reorder_cover_days',
        default=14.0,
        help='How low cover has to drop before auto-prep kicks in. '
             '14 days means a product still has two weeks of stock '
             'at the current sales rate. Tighter (e.g. 7 days) means '
             'fewer drafts; looser (e.g. 30 days) means more frequent '
             'top-up orders.')

    def set_values(self):
        super().set_values()
        param = self.env['ir.config_parameter'].sudo()
        user_ids = ','.join(
            str(i) for i in self.pharmacy_expiry_notify_user_ids.ids)
        param.set_param(
            'shafic_pharmacy_reports.expiry_notify_user_ids', user_ids)

    @api.model
    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo()
        user_ids = param.get_param(
            'shafic_pharmacy_reports.expiry_notify_user_ids', '')
        if user_ids:
            ids = [int(i) for i in user_ids.split(',') if i.strip().isdigit()]
            res['pharmacy_expiry_notify_user_ids'] = [(6, 0, ids)]
        return res

    def action_send_test_digest(self):
        """Send the weekly digest right now to confirm it looks right."""
        self.env['pharmacy.cron'].cron_weekly_digest()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Weekly Digest',
                'message': 'Digest email sent to the configured '
                           'expiry-notification recipients.',
                'type': 'success',
                'sticky': False,
            },
        }
