# -*- coding: utf-8 -*-
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class PharmacyBonusScorecard(models.AbstractModel):
    """Computes the inventory team bonus scorecard for a given month.

    Three KPIs, each scored against configurable targets and translated
    into a share of the monthly team pool:

    * Expiry write-off rate  = expired stock value / average stock value
    * Near-expiry caught      = near-expiry value cleared before expiry
    * Data completeness        = % active products with barcode, internal
                                 reference and (where tracked) lot/batch
    """
    _name = 'pharmacy.bonus.scorecard'
    _description = 'Pharmacy Inventory Bonus Scorecard'

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_param(self, key, default):
        value = self.env['ir.config_parameter'].sudo().get_param(
            'shafic_pharmacy_reports.%s' % key)
        if value in (None, False, ''):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @api.model
    def _config(self):
        return {
            'pool': self._get_param('bonus_pool', 255.0),
            'expiry_target': self._get_param('bonus_expiry_target', 1.4),
            'expiry_baseline': self._get_param('bonus_expiry_baseline', 2.0),
            'catch_target': self._get_param('bonus_catch_target', 80.0),
            'data_target': self._get_param('bonus_data_target', 98.0),
            'data_floor': self._get_param('bonus_data_floor', 90.0),
            'w_expiry': self._get_param('bonus_weight_expiry', 115.0),
            'w_catch': self._get_param('bonus_weight_catch', 50.0),
            'w_data': self._get_param('bonus_weight_data', 90.0),
        }

    # ------------------------------------------------------------------
    # Scoring math
    # ------------------------------------------------------------------
    @staticmethod
    def _score_descending(value, target, baseline):
        """Score where lower is better (e.g. write-off rate).

        Full (1.0) at or below target, zero at or above baseline,
        linear in between.
        """
        if baseline <= target:
            return 1.0 if value <= target else 0.0
        if value <= target:
            return 1.0
        if value >= baseline:
            return 0.0
        return (baseline - value) / (baseline - target)

    @staticmethod
    def _score_ascending(value, target, floor):
        """Score where higher is better (e.g. data completeness).

        Full (1.0) at or above target, zero at or below floor,
        linear in between.
        """
        if target <= floor:
            return 1.0 if value >= target else 0.0
        if value >= target:
            return 1.0
        if value <= floor:
            return 0.0
        return (value - floor) / (target - floor)

    # ------------------------------------------------------------------
    # KPI measurements
    # ------------------------------------------------------------------
    @api.model
    def _date_bounds(self, year, month):
        period_start = date(year, month, 1)
        period_end = period_start + relativedelta(months=1)
        return period_start, period_end

    @api.model
    def _average_stock_value(self, company_id=False, year=False, month=False):
        """Average on-hand stock value for the given month.

        Uses the daily stock-value snapshots written by the daily cron.
        Falls back to a live point-in-time read if no daily snapshots
        are available for the period (e.g. before the cron has run).

        :param year: target year. If omitted, today's year is used.
        :param month: target month. If omitted, today's month is used.
        """
        today = fields.Date.context_today(self)
        if not year:
            year = today.year
        if not month:
            month = today.month

        period_start = date(year, month, 1)
        period_end = period_start + relativedelta(months=1)

        domain = [
            ('capture_date', '>=', period_start),
            ('capture_date', '<', period_end),
        ]
        if company_id:
            domain.append(('company_id', '=', company_id))
        daily = self.env['pharmacy.stock.value.daily'].sudo().search(domain)
        if daily:
            values = daily.mapped('stock_value')
            return sum(values) / len(values)

        # Fallback: no daily snapshots for the period. Use the live
        # stock-position read so the scorecard still works on day one.
        pos_domain = []
        if company_id:
            pos_domain.append(('company_id', '=', company_id))
        positions = self.env['report.pharmacy.stock.position'].search(
            pos_domain)
        return sum(positions.mapped('stock_value'))

    @api.model
    def _expired_value(self, company_id=False, year=False, month=False):
        """Value of currently expired stock still on hand, less any
        approved exclusions for the given period.

        Approved exclusions (uncontrollable losses such as fridge
        failure or short-dated deliveries) are deducted so the bonus
        rate reflects only losses the team could have prevented. The
        underlying expired stock is unchanged; only the bonus
        denominator is adjusted.
        """
        domain = [('expiry_bucket', '=', 'expired')]
        if company_id:
            domain.append(('company_id', '=', company_id))
        expired = self.env['report.pharmacy.expiry'].sudo().search(domain)
        value = sum(expired.mapped('stock_value'))

        # Subtract approved exclusions for this period.
        today = fields.Date.context_today(self)
        target_year = year or today.year
        target_month = month or today.month
        excl_domain = [
            ('state', '=', 'approved'),
            ('year', '=', target_year),
            ('month', '=', target_month),
        ]
        if company_id:
            excl_domain.append(('company_id', '=', company_id))
        exclusions = self.env['pharmacy.expiry.exclusion'].sudo().search(excl_domain)
        excluded_total = sum(exclusions.mapped('excluded_value'))
        return max(value - excluded_total, 0.0)

    @api.model
    def _exclusion_total(self, company_id=False, year=False, month=False):
        """Approved exclusion total for the given period.

        Exposed so the scorecard UI can show users how much was
        deducted, instead of silently lowering the rate.
        """
        today = fields.Date.context_today(self)
        target_year = year or today.year
        target_month = month or today.month
        domain = [
            ('state', '=', 'approved'),
            ('year', '=', target_year),
            ('month', '=', target_month),
        ]
        if company_id:
            domain.append(('company_id', '=', company_id))
        exclusions = self.env['pharmacy.expiry.exclusion'].sudo().search(domain)
        return sum(exclusions.mapped('excluded_value'))

    @api.model
    def _near_expiry_value(self, company_id=False):
        """Value of near-expiry stock (within the alert window, not yet
        expired) — the pool of stock the team is expected to clear."""
        domain = [('expiry_bucket', 'in', ('30', '60', '90', '180'))]
        if company_id:
            domain.append(('company_id', '=', company_id))
        near = self.env['report.pharmacy.expiry'].sudo().search(domain)
        return sum(near.mapped('stock_value'))

    @api.model
    def _catch_action_value(self, company_id=False, year=False, month=False):
        """Total value of catch actions recorded in the given month.

        Each row in ``pharmacy.expiry.action`` represents real activity
        on near-expiry stock — a discount applied, a supplier return
        arranged, a transfer, or a clearance. Summing the value at risk
        of these actions is the bonus catch-early numerator.
        """
        today = fields.Date.context_today(self)
        target_year = year or today.year
        target_month = month or today.month
        domain = [
            ('year', '=', target_year),
            ('month', '=', target_month),
        ]
        if company_id:
            domain.append(('company_id', '=', company_id))
        actions = self.env['pharmacy.expiry.action'].sudo().search(domain)
        return sum(actions.mapped('value_at_risk'))

    @api.model
    def _data_completeness(self, company_id=False):
        """Percentage of active stockable products whose data is complete.

        Reads the active rules from ``pharmacy.data.rule`` so the
        bonus calculation stays in step with the data-completeness
        dashboard. A product is complete when its barcode, internal
        reference and (when lot/serial tracked) at least one lot all
        pass the validity rules.
        """
        product_domain = [('active', '=', True), ('type', '=', 'consu')]
        Product = self.env['product.product']
        products = Product.search(product_domain)
        if not products:
            return 100.0
        DataRule = self.env['pharmacy.data.rule']
        complete = 0
        for product in products:
            has_barcode = DataRule.value_is_valid('barcode', product.barcode)
            has_ref = DataRule.value_is_valid(
                'default_code', product.default_code)
            if product.tracking in ('lot', 'serial'):
                lots = self.env['stock.lot'].search([
                    ('product_id', '=', product.id),
                ])
                # At least one lot whose name passes the rule.
                has_lot = any(
                    DataRule.value_is_valid('lot_name', lot.name)
                    for lot in lots) if lots else False
            else:
                has_lot = True
            if has_barcode and has_ref and has_lot:
                complete += 1
        return (complete / len(products)) * 100.0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    @api.model
    def _compute_live(self, company_id=False, year=False, month=False):
        """Compute the three KPIs and payouts from current inventory state.

        Returned figures reflect the live snapshot of stock right now;
        they are the source for both the live scorecard and the monthly
        snapshot capture. The denominator (average stock value) uses
        daily snapshots accumulated for the given period when available.
        """
        cfg = self._config()
        avg_stock = self._average_stock_value(company_id, year, month)
        expired = self._expired_value(company_id, year, month)
        near_value = self._near_expiry_value(company_id)
        exclusion_total = self._exclusion_total(company_id, year, month)
        catch_value = self._catch_action_value(company_id, year, month)

        expiry_rate = (expired / avg_stock * 100.0) if avg_stock else 0.0
        # Catch-early: real actions logged this month against what was
        # at risk. Denominator = recorded actions + actually-expired
        # stock value. If neither exists, score is full (nothing to
        # catch, no expiry). The proxy 'near_value' is retained only
        # for display.
        denom = catch_value + expired
        if denom > 0:
            caught_pct = (catch_value / denom) * 100.0
        else:
            caught_pct = 100.0
        data_pct = self._data_completeness(company_id)

        expiry_score = self._score_descending(
            expiry_rate, cfg['expiry_target'], cfg['expiry_baseline'])
        catch_score = self._score_ascending(
            caught_pct, cfg['catch_target'], 30.0)
        data_score = self._score_ascending(
            data_pct, cfg['data_target'], cfg['data_floor'])

        expiry_pay = round(expiry_score * cfg['w_expiry'], 2)
        catch_pay = round(catch_score * cfg['w_catch'], 2)
        data_pay = round(data_score * cfg['w_data'], 2)
        total_pay = round(expiry_pay + catch_pay + data_pay, 2)
        total_possible = round(
            cfg['w_expiry'] + cfg['w_catch'] + cfg['w_data'], 2)

        return {
            'cfg': cfg,
            'avg_stock': avg_stock,
            'expired': expired,
            'near_value': near_value,
            'exclusion_total': exclusion_total,
            'expiry_rate': expiry_rate,
            'caught_pct': caught_pct,
            'data_pct': data_pct,
            'expiry_score': expiry_score,
            'catch_score': catch_score,
            'data_score': data_score,
            'expiry_pay': expiry_pay,
            'catch_pay': catch_pay,
            'data_pay': data_pay,
            'total_pay': total_pay,
            'total_possible': total_possible,
        }

    @api.model
    def _format_payload(self, year, month, cfg, source, **k):
        """Shape the dict returned to the OWL scorecard client.

        All scores arrive on the same 0-100 scale (the caller is
        responsible for the conversion).
        """
        return {
            'year': year,
            'month': month,
            'source': source,  # 'live' or 'snapshot'
            'pool': cfg['pool'],
            'average_stock_value': round(k['avg_stock'], 2),
            'expired_value': round(k['expired'], 2),
            'near_expiry_value': round(k['near_value'], 2),
            'exclusion_total': round(k.get('exclusion_total', 0.0), 2),
            'kpis': [
                {
                    'name': 'Expiry Write-off Rate',
                    'value': round(k['expiry_rate'], 2),
                    'unit': '%',
                    'target': cfg['expiry_target'],
                    'baseline': cfg['expiry_baseline'],
                    'direction': 'lower is better',
                    'score': round(k['expiry_score'], 1),
                    'weight': cfg['w_expiry'],
                    'earned': k['expiry_pay'],
                },
                {
                    'name': 'Near-Expiry Caught Early',
                    'value': round(k['caught_pct'], 2),
                    'unit': '%',
                    'target': cfg['catch_target'],
                    'baseline': 30.0,
                    'direction': 'higher is better',
                    'score': round(k['catch_score'], 1),
                    'weight': cfg['w_catch'],
                    'earned': k['catch_pay'],
                },
                {
                    'name': 'Data Completeness',
                    'value': round(k['data_pct'], 2),
                    'unit': '%',
                    'target': cfg['data_target'],
                    'baseline': cfg['data_floor'],
                    'direction': 'higher is better',
                    'score': round(k['data_score'], 1),
                    'weight': cfg['w_data'],
                    'earned': k['data_pay'],
                },
            ],
            'total_earned': k['total_pay'],
            'total_possible': k['total_possible'],
        }

    @api.model
    def get_scorecard(self, year=False, month=False, company_id=False):
        """Return the bonus scorecard for the given month.

        Past months (relative to today) are read from a stored snapshot
        when one exists, so the figures match what was actually true at
        that month's end. The current month is always computed live.
        """
        today = fields.Date.context_today(self)
        if not year:
            year = today.year
        if not month:
            month = today.month
        cfg = self._config()

        is_past = (year, month) < (today.year, today.month)
        if is_past:
            domain = [('year', '=', year), ('month', '=', month)]
            if company_id:
                domain.append(('company_id', '=', company_id))
            snap = self.env['pharmacy.bonus.snapshot'].search(
                domain, limit=1)
            if snap:
                return self._format_payload(
                    year, month, cfg, 'snapshot',
                    avg_stock=snap.average_stock_value,
                    expired=snap.expired_value,
                    near_value=snap.near_expiry_value,
                    exclusion_total=snap.exclusion_total,
                    expiry_rate=snap.expiry_rate,
                    caught_pct=snap.catch_pct,
                    data_pct=snap.data_pct,
                    expiry_score=snap.expiry_score,
                    catch_score=snap.catch_score,
                    data_score=snap.data_score,
                    expiry_pay=snap.expiry_pay,
                    catch_pay=snap.catch_pay,
                    data_pay=snap.data_pay,
                    total_pay=snap.total_earned,
                    total_possible=snap.total_possible)
            # past month, no snapshot -> empty zeros so the user is not
            # misled into thinking they have data they don't.
            return {
                'year': year, 'month': month, 'source': 'missing',
                'pool': cfg['pool'],
                'average_stock_value': 0.0, 'expired_value': 0.0,
                'near_expiry_value': 0.0, 'exclusion_total': 0.0,
                'kpis': [
                    {'name': 'Expiry Write-off Rate', 'value': 0, 'unit': '%',
                     'target': cfg['expiry_target'],
                     'baseline': cfg['expiry_baseline'],
                     'direction': 'lower is better', 'score': 0,
                     'weight': cfg['w_expiry'], 'earned': 0.0},
                    {'name': 'Near-Expiry Caught Early', 'value': 0,
                     'unit': '%', 'target': cfg['catch_target'],
                     'baseline': 30.0, 'direction': 'higher is better',
                     'score': 0, 'weight': cfg['w_catch'], 'earned': 0.0},
                    {'name': 'Data Completeness', 'value': 0, 'unit': '%',
                     'target': cfg['data_target'],
                     'baseline': cfg['data_floor'],
                     'direction': 'higher is better', 'score': 0,
                     'weight': cfg['w_data'], 'earned': 0.0},
                ],
                'total_earned': 0.0,
                'total_possible': round(
                    cfg['w_expiry'] + cfg['w_catch'] + cfg['w_data'], 2),
            }

        live = self._compute_live(company_id, year, month)
        live.pop('cfg', None)
        # Normalize live scores from 0-1 to 0-100 for the unified payload.
        live['expiry_score'] *= 100.0
        live['catch_score'] *= 100.0
        live['data_score'] *= 100.0
        return self._format_payload(year, month, cfg, 'live', **live)

    @api.model
    def capture_month_snapshot(self, year=False, month=False,
                               company_id=False, replace=False):
        """Persist the current live KPI state as the snapshot for the
        given month. Called by the monthly cron with the previous month
        as its target, and available manually for back-fill.

        :param replace: if True, an existing snapshot for the period is
                        overwritten. Default False raises if duplicate.
        """
        today = fields.Date.context_today(self)
        if not year:
            year = today.year
        if not month:
            month = today.month
        if not company_id:
            company_id = self.env.company.id

        live = self._compute_live(company_id, year, month)
        Snapshot = self.env['pharmacy.bonus.snapshot']
        existing = Snapshot.search([
            ('year', '=', year), ('month', '=', month),
            ('company_id', '=', company_id)], limit=1)

        vals = {
            'year': year,
            'month': month,
            'company_id': company_id,
            'capture_date': today,
            'average_stock_value': round(live['avg_stock'], 2),
            'expired_value': round(live['expired'], 2),
            'near_expiry_value': round(live['near_value'], 2),
            'expiry_rate': round(live['expiry_rate'], 2),
            'catch_pct': round(live['caught_pct'], 2),
            'data_pct': round(live['data_pct'], 2),
            'expiry_score': round(live['expiry_score'] * 100.0, 1),
            'catch_score': round(live['catch_score'] * 100.0, 1),
            'data_score': round(live['data_score'] * 100.0, 1),
            'expiry_pay': live['expiry_pay'],
            'catch_pay': live['catch_pay'],
            'data_pay': live['data_pay'],
            'total_earned': live['total_pay'],
            'total_possible': live['total_possible'],
            'exclusion_total': round(live.get('exclusion_total', 0.0), 2),
        }
        if existing:
            if replace:
                existing.write(vals)
                return existing
            return existing
        return Snapshot.create(vals)
