# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PharmacyCron(models.AbstractModel):
    """Container for all scheduled (ir.cron) pharmacy maintenance jobs.

    Keeping cron logic in a single abstract model avoids scattering
    cron entry-points across operational models and makes the
    scheduled-action data file easy to audit.
    """
    _name = 'pharmacy.cron'
    _description = 'Pharmacy Scheduled Jobs'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_int_param(self, key, default):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'shafic_pharmacy_reports.%s' % key, default)
        try:
            return int(float(param))
        except (TypeError, ValueError):
            return default

    @api.model
    def _notify_users(self, group_xmlid, subject, body):
        """Post an internal note + activity to every user of a group."""
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        if not group or not group.users:
            return
        for user in group.users:
            self.env['mail.activity'].sudo().create({
                'activity_type_id': self.env.ref(
                    'mail.mail_activity_data_todo').id,
                'res_model_id': self.env['ir.model']._get(
                    'res.users').id,
                'res_id': user.id,
                'user_id': user.id,
                'summary': subject,
                'note': body,
                'date_deadline': fields.Date.context_today(self),
            })

    # ------------------------------------------------------------------
    # 1. Expiry checks
    # ------------------------------------------------------------------
    @api.model
    def cron_expiry_check(self):
        """Scan lots approaching expiry and raise internal alerts."""
        alert_days = self._get_int_param('expiry_alert_days', 90)
        limit_date = fields.Date.add(
            fields.Date.context_today(self), days=alert_days)
        lots = self.env['stock.lot'].search([
            ('expiration_date', '!=', False),
            ('expiration_date', '<=', limit_date),
        ])
        # Only keep lots that still have stock on hand.
        flagged = lots.filtered(lambda l: l.product_qty > 0)
        if not flagged:
            _logger.info('Pharmacy expiry cron: no lots near expiry.')
            return True
        lines = []
        for lot in flagged[:50]:
            lines.append('- %s | Batch %s | Exp %s | Qty %s' % (
                lot.product_id.display_name, lot.name or '-',
                lot.expiration_date, lot.product_qty))
        body = _(
            '%(count)s batch(es) are within %(days)s days of expiry:'
            '<br/>%(lines)s'
        ) % {
            'count': len(flagged),
            'days': alert_days,
            'lines': '<br/>'.join(lines),
        }
        self._notify_users(
            'shafic_pharmacy_reports.group_inventory_officer',
            _('Pharmacy Expiry Alert'), body)
        _logger.info('Pharmacy expiry cron: %s lots flagged.', len(flagged))
        return True

    # ------------------------------------------------------------------
    # 2. Reorder alerts
    # ------------------------------------------------------------------
    @api.model
    def cron_reorder_alert(self):
        """Flag products that have fallen at/below their reorder minimum."""
        self.env['report.pharmacy.reorder'].flush_model()
        reorder_lines = self.env['report.pharmacy.reorder'].sudo().search([
            ('needs_reorder', '=', True),
        ])
        if not reorder_lines:
            _logger.info('Pharmacy reorder cron: nothing to reorder.')
            return True
        lines = []
        for rec in reorder_lines[:50]:
            lines.append('- %s | On hand %s | Min %s | Suggest %s' % (
                rec.product_id.display_name, rec.qty_available,
                rec.reorder_min, rec.suggested_qty))
        body = _(
            '%(count)s product(s) require reordering:<br/>%(lines)s'
        ) % {'count': len(reorder_lines), 'lines': '<br/>'.join(lines)}
        self._notify_users(
            'shafic_pharmacy_reports.group_inventory_officer',
            _('Pharmacy Reorder Alert'), body)
        _logger.info('Pharmacy reorder cron: %s products flagged.',
                     len(reorder_lines))
        return True

    # ------------------------------------------------------------------
    # 3. Dashboard / movement analysis refresh
    # ------------------------------------------------------------------
    @api.model
    def cron_refresh_analysis(self):
        """Rebuild the stored fast/slow/dead-stock movement analysis and
        refresh customer segmentation."""
        self.env['report.pharmacy.stock.movement'].sudo().refresh_movement_analysis()
        partners = self.env['res.partner'].search([
            ('customer_rank', '>', 0),
        ])
        if partners:
            partners._compute_customer_segment()
        _logger.info('Pharmacy analysis cron: movement analysis and '
                     'customer segments refreshed.')
        return True

    # ------------------------------------------------------------------
    # 4. Insurance status sync
    # ------------------------------------------------------------------
    @api.model
    def cron_insurance_sync(self):
        """Schedule follow-up activities for stale pending insurance claims."""
        stale_date = fields.Date.subtract(
            fields.Date.context_today(self), days=7)
        claims = self.env['pharmacy.insurance.claim'].sudo().search([
            ('state', 'in', ('submitted', 'partial')),
            ('claim_date', '<=', stale_date),
        ])
        for claim in claims:
            if claim.activity_ids:
                continue
            claim.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Follow up pending insurance claim'),
                note=_('This claim has been pending for over 7 days.'),
                user_id=claim.create_uid.id or self.env.uid)
        _logger.info('Pharmacy insurance cron: %s claims followed up.',
                     len(claims))
        return True

    # ------------------------------------------------------------------
    # 5. Monthly bonus snapshot
    # ------------------------------------------------------------------
    @api.model
    def cron_bonus_snapshot(self):
        """Capture a bonus scorecard snapshot for the previous month.

        Runs on the first of each month. Picks up the month that just
        closed and stores the figures so the scorecard can show real
        history rather than today's live state.
        """
        today = fields.Date.context_today(self)
        # Previous month
        if today.month == 1:
            prev_year, prev_month = today.year - 1, 12
        else:
            prev_year, prev_month = today.year, today.month - 1

        Scorecard = self.env['pharmacy.bonus.scorecard']
        captured = 0
        for company in self.env['res.company'].search([]):
            Scorecard.with_company(company).capture_month_snapshot(
                prev_year, prev_month, company.id, replace=False)
            captured += 1
        _logger.info(
            'Pharmacy bonus cron: snapshot captured for %s/%s '
            '(%s companies).', prev_month, prev_year, captured)
        return True

    # ------------------------------------------------------------------
    # 6. Daily stock-value capture (denominator for the bonus scheme)
    # ------------------------------------------------------------------
    @api.model
    def cron_capture_daily_stock_value(self):
        """Record today's total inventory value per company.

        These daily rows feed the period-average stock value used as the
        denominator for the expiry write-off rate. If a row already
        exists for today (e.g. the cron has already run), it is updated
        with the latest figure rather than duplicated.
        """
        today = fields.Date.context_today(self)
        Position = self.env['report.pharmacy.stock.position']
        Daily = self.env['pharmacy.stock.value.daily']
        captured = 0
        for company in self.env['res.company'].search([]):
            positions = Position.with_company(company).search([
                ('company_id', '=', company.id),
            ])
            value = sum(positions.mapped('stock_value'))
            existing = Daily.sudo().search([
                ('capture_date', '=', today),
                ('company_id', '=', company.id),
            ], limit=1)
            vals = {
                'capture_date': today,
                'company_id': company.id,
                'stock_value': round(value, 2),
            }
            if existing:
                existing.write(vals)
            else:
                Daily.create(vals)
            captured += 1
        _logger.info(
            'Pharmacy stock-value cron: captured for %s companies '
            '(date %s).', captured, today)
        return True

    # ------------------------------------------------------------------
    # 7. Weekly digest email
    # ------------------------------------------------------------------
    @api.model
    def cron_weekly_digest(self):
        """Send a one-page weekly digest to the configured recipients.

        Runs every Monday. Reuses the expiry-notification recipient
        list rather than introducing yet another setting. Each company
        produces and sends its own digest.
        """
        for company in self.env['res.company'].search([]):
            try:
                self.with_company(company)._send_weekly_digest_for_company(
                    company)
            except Exception as exc:
                _logger.exception(
                    'Pharmacy weekly digest failed for company %s: %s',
                    company.name, exc)
        return True

    @api.model
    def _send_weekly_digest_for_company(self, company):
        """Build and send the digest for one company."""
        recipients = self._resolve_digest_recipients()
        if not recipients:
            _logger.info(
                'Pharmacy weekly digest: no recipients configured for '
                'company %s — skipping.', company.name)
            return False

        today = fields.Date.context_today(self)
        body = self._render_digest_body(company, today)
        subject = _(
            'Pharmacy weekly digest — week of %s') % today.strftime('%d %b %Y')

        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body,
            'email_from': (company.email
                           or self.env.user.email_formatted
                           or 'noreply@example.com'),
            'email_to': ','.join(r.email for r in recipients if r.email),
        })
        mail.send()
        _logger.info(
            'Pharmacy weekly digest: sent to %s recipient(s) for %s.',
            len(recipients), company.name)
        return True

    # ------------------------------------------------------------------
    # 8. Anomaly alerts - run daily, alert on unusual patterns
    # ------------------------------------------------------------------
    @api.model
    def cron_snapshot_cost_anomalies(self):
        """Capture today's cost/price anomalies into the history table,
        then prune old snapshots. Runs daily.

        This is what powers the date-range filter and the "New Today"
        view on the Anomaly History report.
        """
        Snapshot = self.env['pharmacy.cost.anomaly.snapshot']
        try:
            Snapshot.capture_snapshot()
            Snapshot.cleanup_old_snapshots(keep_days=180)
        except Exception as exc:
            _logger.exception('Cost anomaly snapshot failed: %s', exc)
        # Layer 2: alert on products newly set up with a cost/UoM
        # mismatch (cost >= price or negative cost), so imports and new
        # products are caught the day after they appear.
        try:
            self._alert_new_cost_setup_mismatches()
        except Exception as exc:
            _logger.exception('New cost-setup mismatch alert failed: %s', exc)
        # Refresh the "Products to Fix" worklist flag across the catalog.
        try:
            self.env['product.template'].flag_cost_issues()
        except Exception as exc:
            _logger.exception('Cost-issue flagging failed: %s', exc)
        return True

    @api.model
    def _alert_new_cost_setup_mismatches(self):
        """Email the digest recipients about products whose cost setup
        looks wrong and that are NEW today in the anomaly snapshot.

        Uses the snapshot's is_new flag plus the below-cost / negative
        signals so we only notify on freshly-appeared problems, not the
        entire backlog every day.
        """
        recipients = self._resolve_digest_recipients()
        if not recipients:
            return False
        today = fields.Date.context_today(self)
        Snapshot = self.env['pharmacy.cost.anomaly.snapshot']
        new_rows = Snapshot.search([
            ('snapshot_date', '=', today),
            ('is_new', '=', True),
            '|',
            ('flag_below_cost', '=', True),
            ('current_cost', '<', 0),
        ])
        if not new_rows:
            return False
        # De-dup by product, build a compact list for the email.
        seen = set()
        lines = []
        for r in new_rows:
            if r.product_id.id in seen:
                continue
            seen.add(r.product_id.id)
            lines.append(
                '<li><strong>%s</strong> — cost %.4f vs price %.4f</li>' % (
                    r.product_id.display_name or '',
                    r.current_cost or 0.0,
                    r.current_price or 0.0))
        body = (
            '<p>%d product(s) appeared today with a cost setup that looks '
            'wrong (cost at/above price, or negative cost). These are '
            'usually products costed per pack but sold per unit. Please '
            'review the unit of measure / cost:</p><ul>%s</ul>'
        ) % (len(seen), ''.join(lines))
        emails = [r.email for r in recipients if r.email]
        if not emails:
            return False
        self.env['mail.mail'].sudo().create({
            'subject': 'Pharmacy: %d new product(s) with a cost/unit issue'
                       % len(seen),
            'body_html': body,
            'email_to': ','.join(emails),
        }).send()
        return True

    @api.model
    def cron_anomaly_alerts(self):
        """Detect unusual patterns and alert recipients.

        Runs three checks:
          1. Refund rate per cashier far above peer average
          2. Category write-off doubled week over week
          3. Daily returns volume far above trailing 4-week average

        Each detected anomaly is suppressed for 7 days using a config
        parameter marker so the team isn't spammed with the same alert
        on consecutive days. Recipients come from the expiry-notify
        list to keep the alerting surface area small.
        """
        for company in self.env['res.company'].search([]):
            try:
                self.with_company(company)._run_anomaly_checks_for_company(
                    company)
            except Exception as exc:
                _logger.exception(
                    'Anomaly alerts failed for company %s: %s',
                    company.name, exc)
        return True

    @api.model
    def _run_anomaly_checks_for_company(self, company):
        """Run the three anomaly checks for one company."""
        recipients = self._resolve_digest_recipients()
        if not recipients:
            return False
        alerts = []
        alerts += self._check_cashier_refund_spike(company)
        alerts += self._check_category_writeoff_jump(company)
        alerts += self._check_returns_spike(company)
        for alert in alerts:
            self._send_anomaly_alert(company, alert, recipients)
        return True

    @api.model
    def _alert_already_sent(self, key):
        """Return True if this alert key was sent within the last 7 days."""
        param_name = 'shafic_pharmacy_reports.alert_sent.%s' % key
        last = self.env['ir.config_parameter'].sudo().get_param(param_name)
        if not last:
            return False
        try:
            last_dt = fields.Datetime.from_string(last)
        except Exception:
            return False
        delta = fields.Datetime.now() - last_dt
        return delta.days < 7

    @api.model
    def _mark_alert_sent(self, key):
        param_name = 'shafic_pharmacy_reports.alert_sent.%s' % key
        self.env['ir.config_parameter'].sudo().set_param(
            param_name, fields.Datetime.to_string(fields.Datetime.now()))

    @api.model
    def _check_cashier_refund_spike(self, company):
        """Flag cashiers whose 7-day refund rate is ≥ 3x peer average
        and who have at least 5 refunds in the window."""
        self.env.cr.execute("""
            WITH last7 AS (
                SELECT u.id AS user_id, u.login AS login,
                       COUNT(*) FILTER (WHERE o.amount_total < 0) AS refunds,
                       COUNT(*) AS orders
                FROM pos_order o
                JOIN res_users u ON o.user_id = u.id
                WHERE o.company_id = %s
                  AND o.date_order >= (CURRENT_DATE - INTERVAL '7 days')
                  AND o.state IN ('paid', 'done', 'invoiced')
                GROUP BY u.id, u.login
            )
            SELECT user_id, login, refunds, orders,
                   CASE WHEN orders > 0
                        THEN refunds::float / orders ELSE 0 END AS rate
              FROM last7
        """, (company.id,))
        rows = self.env.cr.dictfetchall()
        if not rows:
            return []
        avg_rate = (sum(r['rate'] for r in rows) / len(rows)) if rows else 0.0
        alerts = []
        for r in rows:
            if r['refunds'] < 5:
                continue
            if avg_rate <= 0:
                continue
            if r['rate'] < avg_rate * 3.0:
                continue
            key = 'cashier_refund_%s_%s' % (company.id, r['user_id'])
            if self._alert_already_sent(key):
                continue
            alerts.append({
                'key': key,
                'subject': _(
                    'Pharmacy alert: refund rate spike — %s') % r['login'],
                'body': _(
                    'Cashier <strong>%(user)s</strong> had a refund rate of '
                    '<strong>%(rate).1f%%</strong> over the last 7 days '
                    '(%(refunds)d refunds in %(orders)d orders). '
                    'Peer average over the same window is '
                    '<strong>%(avg).1f%%</strong>. Investigate whether this '
                    'is a training gap, a system issue, or something else.'
                ) % {
                    'user': r['login'],
                    'rate': r['rate'] * 100.0,
                    'refunds': r['refunds'],
                    'orders': r['orders'],
                    'avg': avg_rate * 100.0,
                },
            })
        return alerts

    @api.model
    def _check_category_writeoff_jump(self, company):
        """Flag categories whose expired-stock value this week is ≥ 2x
        last week's and ≥ $50."""
        # We compare the value of stock written off (moved to an
        # inventory-loss location) in the last 7 days against the prior
        # 7 days, grouped by pharmacy category.
        self.env.cr.execute("""
            SELECT t.pharmacy_category_id AS category,
                   SUM(sm.product_qty *
                       COALESCE(
                           (p.standard_price ->> sm.company_id::text)::numeric,
                           0))
                   AS value
              FROM stock_move sm
              JOIN product_product p ON sm.product_id = p.id
              JOIN product_template t ON p.product_tmpl_id = t.id
              JOIN stock_location dest ON sm.location_dest_id = dest.id
              WHERE sm.state = 'done'
                AND sm.company_id = %s
                AND dest.usage = 'inventory'
                AND sm.date >= (CURRENT_DATE - INTERVAL '7 days')
              GROUP BY t.pharmacy_category_id
        """, (company.id,))
        this_week = {r[0]: r[1] or 0.0 for r in self.env.cr.fetchall()}
        self.env.cr.execute("""
            SELECT t.pharmacy_category_id AS category,
                   SUM(sm.product_qty *
                       COALESCE(
                           (p.standard_price ->> sm.company_id::text)::numeric,
                           0))
                   AS value
              FROM stock_move sm
              JOIN product_product p ON sm.product_id = p.id
              JOIN product_template t ON p.product_tmpl_id = t.id
              JOIN stock_location dest ON sm.location_dest_id = dest.id
              WHERE sm.state = 'done'
                AND sm.company_id = %s
                AND dest.usage = 'inventory'
                AND sm.date >= (CURRENT_DATE - INTERVAL '14 days')
                AND sm.date <  (CURRENT_DATE - INTERVAL '7 days')
              GROUP BY t.pharmacy_category_id
        """, (company.id,))
        last_week = {r[0]: r[1] or 0.0 for r in self.env.cr.fetchall()}

        # Resolve category ids -> names for readable alerts. Keys in the
        # week maps are pharmacy.product.category ids (or None).
        cat_ids = [k for k in this_week.keys() if k]
        cat_names = {}
        if cat_ids:
            for cat in self.env['pharmacy.product.category'].browse(
                    cat_ids).exists():
                cat_names[cat.id] = cat.name

        alerts = []
        for cat, this_val in this_week.items():
            last_val = last_week.get(cat, 0.0)
            if this_val < 50.0:
                continue
            if last_val <= 0:
                continue
            if this_val < last_val * 2.0:
                continue
            cat_label = cat_names.get(cat, 'Uncategorised')
            key = 'category_writeoff_%s_%s' % (company.id, cat or 'none')
            if self._alert_already_sent(key):
                continue
            alerts.append({
                'key': key,
                'subject': _(
                    'Pharmacy alert: write-off doubled in %s') % cat_label,
                'body': _(
                    'Write-offs in the <strong>%(cat)s</strong> category '
                    'jumped from <strong>$%(last).2f</strong> last week '
                    'to <strong>$%(this).2f</strong> this week (≥ 2x). '
                    'Check whether a batch went bad, a fridge failed, or '
                    'a recall is in progress.'
                ) % {
                    'cat': cat_label,
                    'last': last_val,
                    'this': this_val,
                },
            })
        return alerts

    @api.model
    def _check_returns_spike(self, company):
        """Flag yesterday's return count if it's ≥ 3x the trailing
        4-week daily average and ≥ 5 returns."""
        self.env.cr.execute("""
            SELECT
                COUNT(*) FILTER (
                    WHERE o.date_order::date = CURRENT_DATE - 1
                    AND o.amount_total < 0) AS yesterday_returns,
                COUNT(*) FILTER (
                    WHERE o.date_order::date >= CURRENT_DATE - 29
                    AND o.date_order::date <= CURRENT_DATE - 2
                    AND o.amount_total < 0) AS prior_returns
            FROM pos_order o
            WHERE o.company_id = %s
              AND o.state IN ('paid', 'done', 'invoiced')
        """, (company.id,))
        row = self.env.cr.fetchone()
        if not row:
            return []
        yesterday, prior_28 = row
        if yesterday < 5:
            return []
        avg_per_day = (prior_28 or 0) / 28.0
        if avg_per_day <= 0:
            return []
        if yesterday < avg_per_day * 3.0:
            return []
        key = 'returns_spike_%s' % company.id
        if self._alert_already_sent(key):
            return []
        return [{
            'key': key,
            'subject': _('Pharmacy alert: returns spike yesterday'),
            'body': _(
                'Yesterday saw <strong>%(y)d returns</strong> — '
                'roughly <strong>%(mult).1fx</strong> the trailing '
                '28-day daily average of <strong>%(avg).1f</strong>. '
                'Check whether a single product or cashier is driving '
                'this.'
            ) % {
                'y': yesterday,
                'mult': yesterday / avg_per_day,
                'avg': avg_per_day,
            },
        }]

    @api.model
    def _send_anomaly_alert(self, company, alert, recipients):
        """Send one anomaly alert email and mark the key as sent."""
        body = """
<div style="font-family:Arial,sans-serif;font-size:14px;color:#222;
            max-width:560px;">
  <h3 style="color:#c0392b;margin:0 0 12px 0;">%(subject)s</h3>
  <div>%(body)s</div>
  <p style="color:#888;font-size:12px;margin-top:20px;
            border-top:1px solid #ddd;padding-top:10px;">
    %(company)s · Generated automatically by Pharmacy POS Reports.
  </p>
</div>""" % {
            'subject': alert['subject'],
            'body': alert['body'],
            'company': company.name,
        }
        mail = self.env['mail.mail'].sudo().create({
            'subject': alert['subject'],
            'body_html': body,
            'email_from': (company.email
                           or self.env.user.email_formatted
                           or 'noreply@example.com'),
            'email_to': ','.join(r.email for r in recipients if r.email),
        })
        mail.send()
        self._mark_alert_sent(alert['key'])
        _logger.info('Anomaly alert sent: %s', alert['key'])

    @api.model
    def _resolve_digest_recipients(self):
        """Return the users who should receive the digest.

        Reads from the expiry-notification list to avoid a duplicate
        setting. Falls back to all Pharmacy Admins when the list is
        empty so the digest still goes somewhere useful.
        """
        param = self.env['ir.config_parameter'].sudo().get_param(
            'shafic_pharmacy_reports.expiry_notify_user_ids', '')
        ids = [int(x) for x in param.split(',') if x.strip().isdigit()]
        users = self.env['res.users'].browse(ids).exists()
        if users:
            return users
        admin_group = self.env.ref(
            'shafic_pharmacy_reports.group_pharmacy_admin',
            raise_if_not_found=False)
        if admin_group:
            return admin_group.users
        return self.env['res.users']

    @api.model
    def _render_digest_body(self, company, today):
        """Compose the digest HTML.

        Kept deliberately compact: managers either read this on a phone
        before opening Odoo or they don't read it at all. Headline
        figures, top issues, then the link.
        """
        Position = self.env['report.pharmacy.stock.position']
        Expiry = self.env['report.pharmacy.expiry']
        Reorder = self.env['report.pharmacy.reorder']
        Scorecard = self.env['pharmacy.bonus.scorecard']
        Completeness = self.env['report.pharmacy.data.completeness']

        # Stock value, expired and near-expiry
        positions = Position.search([('company_id', '=', company.id)])
        stock_value = sum(positions.mapped('stock_value'))
        expired = Expiry.search([
            ('company_id', '=', company.id),
            ('expiry_bucket', '=', 'expired'),
        ])
        expired_value = sum(expired.mapped('stock_value'))
        expired_margin = sum(expired.mapped('margin_lost'))
        near = Expiry.search([
            ('company_id', '=', company.id),
            ('expiry_bucket', 'in', ('30', '60')),
        ])
        near_value = sum(near.mapped('stock_value'))

        # Reorder shortfall
        reorder_rows = Reorder.search([
            ('company_id', '=', company.id),
        ])
        below_min = [r for r in reorder_rows if (r.shortage or 0) > 0]
        reorder_count = len(below_min)

        # Bonus scorecard for current month
        scorecard = Scorecard.get_scorecard(today.year, today.month, company.id)
        total_earned = scorecard.get('total_earned', 0.0)
        total_possible = scorecard.get('total_possible', 0.0)

        # Data completeness summary
        comp = Completeness.sudo().get_completeness_summary(company.id)

        # Worst pharmacy category for completeness
        by_cat = comp.get('by_category') or []
        worst_cat = by_cat[0] if by_cat else None

        # Bonus rate vs target
        expiry_kpi = next(
            (k for k in scorecard.get('kpis', [])
             if 'Expiry' in k.get('name', '')), {})
        expiry_rate = expiry_kpi.get('value', 0)
        expiry_target = expiry_kpi.get('target', 0)

        money = lambda v: '$%s' % '{:,.2f}'.format(v or 0)

        worst_cat_html = ''
        if worst_cat:
            worst_cat_html = (
                '<tr><td style="padding:6px 12px;">Weakest data category</td>'
                '<td style="padding:6px 12px; text-align:right;">'
                '<strong>%s</strong> — %s%% complete '
                '(%s incomplete)</td></tr>') % (
                worst_cat.get('label', ''),
                worst_cat.get('pct_complete', 0),
                worst_cat.get('incomplete', 0))

        return """
<div style="font-family:Arial,sans-serif;font-size:14px;color:#222;
            max-width:640px;">
  <h2 style="color:#0B7A75;margin:0 0 8px 0;">Pharmacy Weekly Digest</h2>
  <p style="color:#888;margin:0 0 18px 0;">
    Week of %(week_of)s &middot; %(company)s
  </p>

  <h3 style="color:#0B7A75;margin:18px 0 6px 0;">Headlines</h3>
  <table style="width:100%%;border-collapse:collapse;background:#f7f7f7;">
    <tr><td style="padding:6px 12px;">Total stock value</td>
        <td style="padding:6px 12px;text-align:right;"><strong>%(stock)s</strong></td></tr>
    <tr><td style="padding:6px 12px;">Expired stock on hand</td>
        <td style="padding:6px 12px;text-align:right;color:#c0392b;"><strong>%(expired)s</strong></td></tr>
    <tr><td style="padding:6px 12px;">Margin lost to expiry</td>
        <td style="padding:6px 12px;text-align:right;color:#c0392b;"><strong>%(margin)s</strong></td></tr>
    <tr><td style="padding:6px 12px;">Near-expiry (next 60 days)</td>
        <td style="padding:6px 12px;text-align:right;color:#d68910;"><strong>%(near)s</strong></td></tr>
    <tr><td style="padding:6px 12px;">Expiry rate vs target</td>
        <td style="padding:6px 12px;text-align:right;"><strong>%(rate)s%% / %(target)s%%</strong></td></tr>
    <tr><td style="padding:6px 12px;">Products below reorder min</td>
        <td style="padding:6px 12px;text-align:right;"><strong>%(reorder)s</strong></td></tr>
  </table>

  <h3 style="color:#0B7A75;margin:18px 0 6px 0;">Data Completeness</h3>
  <table style="width:100%%;border-collapse:collapse;background:#f7f7f7;">
    <tr><td style="padding:6px 12px;">Overall</td>
        <td style="padding:6px 12px;text-align:right;"><strong>%(comp_pct)s%%</strong>
        (%(comp_inc)s incomplete of %(comp_total)s)</td></tr>
    <tr><td style="padding:6px 12px;">Missing barcode / ref / lot</td>
        <td style="padding:6px 12px;text-align:right;">
        %(mb)s / %(mr)s / %(ml)s</td></tr>
    %(worst_cat_html)s
  </table>

  <h3 style="color:#0B7A75;margin:18px 0 6px 0;">Bonus Pool — This Month So Far</h3>
  <p style="margin:6px 0;">
    Team pool earned: <strong>%(earned)s</strong>
    of <strong>%(possible)s</strong>
  </p>

  <p style="color:#888;font-size:12px;margin-top:24px;
            border-top:1px solid #ddd;padding-top:12px;">
    This digest is generated every Monday morning from the Pharmacy
    POS Reports module. Open Odoo for full drill-down and to act on
    any of the figures above.
  </p>
</div>
        """ % {
            'week_of': today.strftime('%d %b %Y'),
            'company': company.name,
            'stock': money(stock_value),
            'expired': money(expired_value),
            'margin': money(expired_margin),
            'near': money(near_value),
            'rate': '%.2f' % expiry_rate,
            'target': '%.2f' % expiry_target,
            'reorder': reorder_count,
            'comp_pct': comp.get('pct_complete', 0),
            'comp_inc': comp.get('incomplete', 0),
            'comp_total': comp.get('total', 0),
            'mb': comp.get('missing_barcode', 0),
            'mr': comp.get('missing_ref', 0),
            'ml': comp.get('missing_lot', 0),
            'worst_cat_html': worst_cat_html,
            'earned': money(total_earned),
            'possible': money(total_possible),
        }

    # ------------------------------------------------------------------
    # 9. Auto-prepare draft purchase orders for hot, low-cover products
    # ------------------------------------------------------------------
    @api.model
    def cron_auto_prepare_orders(self):
        """Daily: prepare draft purchase orders for hot products that
        are running low on stock.

        For each company, identify products meeting ALL of these
        criteria:
          - Trailing-90-day sales velocity in top 20% of priced products
          - Days of cover under 14 days at current sales rate
          - Has a default supplier configured (seller_ids)
          - No pending draft purchase order line for this product
          - Not currently flagged in the Cost/Price Anomaly report
            (don't auto-order when the cost looks wrong)

        Then group candidates by supplier and create ONE draft
        purchase.order per supplier, with chatter explaining the
        reasoning per line. The draft is assigned an Activity for the
        Finance team to review and confirm.

        Hard guard rails:
          - Cap per draft (configurable, default $1000) — exceeds
            triggers a separate over-cap activity for senior approval
            rather than creating a runaway order.
          - One draft per supplier per company per day max — repeated
            runs on the same day update the existing draft instead of
            spawning duplicates.

        Returns the list of pharmacy.auto.prepared.order ids created.
        """
        result_ids = []
        for company in self.env['res.company'].search([]):
            try:
                ids = self.with_company(company)._auto_prepare_for_company(
                    company)
                result_ids += ids
            except Exception as exc:
                _logger.exception(
                    'Auto-prepare PO failed for company %s: %s',
                    company.name, exc)
        return result_ids

    @api.model
    def _auto_prepare_for_company(self, company):
        """Run the auto-prepare flow for one company."""
        Param = self.env['ir.config_parameter'].sudo()
        cap = float(Param.get_param(
            'shafic_pharmacy_reports.auto_reorder_cap', '1000.0') or 1000.0)
        velocity_pct = float(Param.get_param(
            'shafic_pharmacy_reports.auto_reorder_velocity_pct',
            '20.0') or 20.0)
        cover_days = float(Param.get_param(
            'shafic_pharmacy_reports.auto_reorder_cover_days',
            '14.0') or 14.0)

        candidates = self._find_auto_reorder_candidates(
            company, velocity_pct, cover_days)
        if not candidates:
            _logger.info(
                'Auto-prepare PO: no candidates for company %s.',
                company.name)
            return []

        # Group candidates by supplier
        by_supplier = {}
        for c in candidates:
            by_supplier.setdefault(c['supplier_id'], []).append(c)

        created_log_ids = []
        for supplier_id, items in by_supplier.items():
            log_id = self._auto_prepare_supplier_draft(
                company, supplier_id, items, cap)
            if log_id:
                created_log_ids.append(log_id)
        return created_log_ids

    @api.model
    def _find_auto_reorder_candidates(self, company, velocity_pct, cover_days):
        """Return a list of dicts describing products to include.

        Each dict has: product_id, product_name, supplier_id,
        avg_daily_demand, lead_time_days, days_of_cover,
        suggested_qty, unit_cost.

        Uses raw SQL so the candidate selection is a single fast query
        rather than N+1 lookups.
        """
        self.env.cr.execute("""
            WITH sales AS (
                SELECT l.product_id,
                       SUM(l.qty) AS qty_90d,
                       SUM(l.qty) / 90.0 AS avg_daily
                  FROM pos_order_line l
                  JOIN pos_order o ON l.order_id = o.id
                 WHERE o.state IN ('paid', 'done', 'invoiced')
                   AND o.company_id = %(company_id)s
                   AND o.date_order >= (CURRENT_DATE - INTERVAL '90 days')
                 GROUP BY l.product_id
                HAVING SUM(l.qty) > 0
            ),
            ranked AS (
                SELECT product_id, qty_90d, avg_daily,
                       PERCENT_RANK() OVER (ORDER BY qty_90d) AS pct_rank
                  FROM sales
            ),
            hot AS (
                SELECT *
                  FROM ranked
                 WHERE pct_rank >= 1.0 - (%(velocity_pct)s / 100.0)
            ),
            on_hand AS (
                SELECT q.product_id, SUM(q.quantity) AS qty
                  FROM stock_quant q
                  JOIN stock_location loc ON q.location_id = loc.id
                 WHERE loc.usage = 'internal'
                   AND q.company_id = %(company_id)s
                 GROUP BY q.product_id
            ),
            supplier AS (
                SELECT DISTINCT ON (t.id)
                       t.id AS product_tmpl_id,
                       si.partner_id AS supplier_id,
                       COALESCE(si.delay, 7) AS lead_days
                  FROM product_template t
                  JOIN product_supplierinfo si
                       ON si.product_tmpl_id = t.id
                  ORDER BY t.id, si.sequence, si.id
            ),
            pending AS (
                SELECT DISTINCT pol.product_id
                  FROM purchase_order_line pol
                  JOIN purchase_order po ON pol.order_id = po.id
                 WHERE po.state IN ('draft', 'sent', 'to approve',
                                    'purchase')
                   AND po.company_id = %(company_id)s
            )
            SELECT
                p.id AS product_id,
                p.default_code,
                COALESCE(p.default_code || ' - ', '') || t.name AS pname,
                s.supplier_id,
                h.avg_daily,
                s.lead_days,
                CASE WHEN h.avg_daily > 0
                     THEN COALESCE(oh.qty, 0) / h.avg_daily
                     ELSE NULL END AS days_of_cover,
                GREATEST(
                    h.avg_daily * (s.lead_days + 7)
                    - COALESCE(oh.qty, 0),
                    0.0) AS suggested_qty,
                COALESCE(pec.effective_cost, 0.0) AS unit_cost
              FROM hot h
              JOIN product_product p ON h.product_id = p.id
              JOIN product_template t ON p.product_tmpl_id = t.id
              JOIN supplier s ON s.product_tmpl_id = t.id
              LEFT JOIN on_hand oh ON oh.product_id = p.id
              LEFT JOIN product_effective_cost pec
                     ON pec.product_id = p.id
                    AND pec.company_id = t.company_id
             WHERE p.active = TRUE
               AND t.company_id = %(company_id)s
               AND p.id NOT IN (SELECT product_id FROM pending)
               AND (h.avg_daily > 0)
               AND (COALESCE(oh.qty, 0) / h.avg_daily) < %(cover_days)s
        """, {
            'company_id': company.id,
            'velocity_pct': velocity_pct,
            'cover_days': cover_days,
        })
        rows = self.env.cr.dictfetchall()

        # Filter out products currently flagged in the anomaly report
        # — never auto-order with broken cost/price data.
        if rows:
            product_ids = [r['product_id'] for r in rows]
            anomalies = self.env['report.pharmacy.cost.price.anomaly'].sudo().search([
                ('product_id', 'in', product_ids),
                ('company_id', '=', company.id),
            ])
            flagged_ids = set(anomalies.mapped('product_id.id'))
            rows = [r for r in rows if r['product_id'] not in flagged_ids]

        # Round suggested_qty up to whole units and discard tiny suggestions
        out = []
        for r in rows:
            qty = float(r['suggested_qty'] or 0)
            qty = round(qty + 0.5)  # ceiling-ish
            if qty < 1:
                continue
            out.append({
                'product_id': r['product_id'],
                'product_name': r['pname'] or '(unnamed)',
                'supplier_id': r['supplier_id'],
                'avg_daily_demand': float(r['avg_daily'] or 0),
                'lead_time_days': int(r['lead_days'] or 7),
                'days_of_cover': float(r['days_of_cover'] or 0),
                'suggested_qty': qty,
                'unit_cost': float(r['unit_cost'] or 0),
            })
        return out

    @api.model
    def _auto_prepare_supplier_draft(self, company, supplier_id, items, cap):
        """Create or update a single draft PO for one supplier.

        Returns the id of the pharmacy.auto.prepared.order log row, or
        False if nothing was prepared (e.g. cap exceeded).
        """
        Partner = self.env['res.partner']
        supplier = Partner.browse(supplier_id)
        if not supplier.exists():
            return False

        # Check the cap: total cost of all items
        total_cost = sum(it['suggested_qty'] * it['unit_cost']
                         for it in items)
        if total_cost > cap:
            self._notify_over_cap(company, supplier, items, total_cost, cap)
            return False

        # Already a draft today for this supplier+company?
        today = fields.Date.context_today(self)
        Log = self.env['pharmacy.auto.prepared.order']
        existing_log = Log.search([
            ('supplier_id', '=', supplier.id),
            ('company_id', '=', company.id),
            ('prepared_on', '>=', '%s 00:00:00' % today),
        ], limit=1)
        if existing_log and existing_log.purchase_order_id \
                and existing_log.purchase_order_id.state == 'draft':
            # Update the existing draft rather than creating a duplicate
            existing_log.purchase_order_id.order_line.unlink()
            self._populate_po_lines(
                existing_log.purchase_order_id, items)
            existing_log.write({
                'line_count': len(items),
                'total_amount': round(total_cost, 2),
                'reason': self._build_reason_text(items),
            })
            return existing_log.id

        # Create a new draft PO
        order_vals = {
            'partner_id': supplier.id,
            'company_id': company.id,
            'origin': 'Auto-prepared by Pharmacy POS Reports',
        }
        po = self.env['purchase.order'].sudo().create(order_vals)
        self._populate_po_lines(po, items)

        # Post chatter message with full reasoning
        po.message_post(
            body=self._build_reason_html(items),
            subject='Auto-prepared draft — reasoning')

        # Assign an Activity to the Finance team for review
        self._assign_review_activity(po)

        log = Log.create({
            'purchase_order_id': po.id,
            'supplier_id': supplier.id,
            'line_count': len(items),
            'total_amount': round(total_cost, 2),
            'reason': self._build_reason_text(items),
            'company_id': company.id,
        })
        _logger.info(
            'Auto-prepare PO: created draft %s for %s with %s lines '
            '(total %.2f, cap %.2f, company %s).',
            po.name, supplier.name, len(items), total_cost, cap,
            company.name)
        return log.id

    @api.model
    def _populate_po_lines(self, po, items):
        """Add one line per candidate to the purchase order."""
        Product = self.env['product.product']
        for it in items:
            product = Product.browse(it['product_id'])
            self.env['purchase.order.line'].sudo().create({
                'order_id': po.id,
                'product_id': product.id,
                'product_qty': it['suggested_qty'],
                'price_unit': it['unit_cost'],
                'name': '%s (auto: ~%.1f units/day, %.1f days cover)' % (
                    product.display_name,
                    it['avg_daily_demand'],
                    it['days_of_cover']),
                'date_planned': fields.Date.context_today(self),
                'product_uom': product.uom_po_id.id or product.uom_id.id,
            })

    @api.model
    def _build_reason_text(self, items):
        """Plain-text reasoning for the log row."""
        lines = ['%s product(s) auto-prepared:' % len(items)]
        for it in items[:20]:
            lines.append(
                '  - %s: order %s (sells ~%.1f/day, %.1f days cover left)'
                % (it['product_name'], it['suggested_qty'],
                   it['avg_daily_demand'], it['days_of_cover']))
        if len(items) > 20:
            lines.append('  ... and %d more' % (len(items) - 20))
        return '\n'.join(lines)

    @api.model
    def _build_reason_html(self, items):
        """HTML reasoning for the PO chatter."""
        rows = []
        for it in items:
            rows.append(
                '<tr><td style="padding:2px 8px;"><strong>%s</strong></td>'
                '<td style="padding:2px 8px;text-align:right;">%s</td>'
                '<td style="padding:2px 8px;text-align:right;color:#888;">'
                '~%.1f / day</td>'
                '<td style="padding:2px 8px;text-align:right;color:#888;">'
                '%.1f days cover</td></tr>' % (
                    it['product_name'], it['suggested_qty'],
                    it['avg_daily_demand'], it['days_of_cover']))
        return (
            '<p><strong>Auto-prepared draft</strong> — review the '
            'quantities below, then confirm or edit.</p>'
            '<table style="border-collapse:collapse;">' + ''.join(rows)
            + '</table>'
            '<p style="color:#888;font-size:12px;margin-top:8px;">'
            'Criteria: top-velocity products with less than 14 days of '
            'cover at current sales rate. Order quantity is '
            'avg_daily × (lead_time + 7d safety) − on_hand.</p>')

    @api.model
    def _assign_review_activity(self, po):
        """Create a Mail Activity on the PO for the Finance team."""
        finance_group = self.env.ref(
            'shafic_pharmacy_reports.group_finance_team',
            raise_if_not_found=False)
        if not finance_group or not finance_group.users:
            return False
        # Pick the first active finance user as the assignee
        assignee = finance_group.users.filtered(
            lambda u: u.active)[:1]
        if not assignee:
            return False
        activity_type = self.env.ref(
            'mail.mail_activity_data_todo',
            raise_if_not_found=False)
        if not activity_type:
            # Activity types misconfigured; skip silently
            return False
        try:
            po.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=assignee.id,
                summary='Review auto-prepared draft purchase order',
                note='This draft was prepared automatically. Review '
                     'quantities and confirm to send to the supplier, '
                     'or reject and delete if not needed.')
        except Exception as exc:
            _logger.warning(
                'Could not schedule review activity on PO %s: %s',
                po.name, exc)
            return False
        return True

    @api.model
    def _notify_over_cap(self, company, supplier, items, total, cap):
        """When a draft would exceed the cap, send an alert instead of
        silently creating it."""
        recipients = self._resolve_digest_recipients()
        if not recipients:
            return False
        money = lambda v: '$%s' % '{:,.2f}'.format(v or 0)
        body = """
<div style="font-family:Arial,sans-serif;font-size:14px;">
  <h3 style="color:#c0392b;">Auto-prepare PO exceeded cap</h3>
  <p>The auto-reorder routine identified %(n)d hot product(s) needing
  restock from <strong>%(sup)s</strong>, but the total cost would be
  <strong>%(total)s</strong> — over the cap of %(cap)s. No draft was
  created.</p>
  <p>Either raise the cap in Settings, or split the order manually:</p>
  <ul>%(items)s</ul>
</div>""" % {
            'n': len(items),
            'sup': supplier.name,
            'total': money(total),
            'cap': money(cap),
            'items': ''.join(
                '<li>%s — %s units at %s/unit</li>' % (
                    it['product_name'], it['suggested_qty'],
                    money(it['unit_cost']))
                for it in items[:10]),
        }
        self.env['mail.mail'].sudo().create({
            'subject': 'Pharmacy auto-reorder: %s over cap' % supplier.name,
            'body_html': body,
            'email_from': (company.email
                           or self.env.user.email_formatted
                           or 'noreply@example.com'),
            'email_to': ','.join(r.email for r in recipients if r.email),
        }).send()
        _logger.info(
            'Auto-prepare PO: %s candidates for %s exceeded cap '
            '(%.2f > %.2f); alert sent.',
            len(items), supplier.name, total, cap)
        return True
