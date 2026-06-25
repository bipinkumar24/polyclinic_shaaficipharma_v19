# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PharmacyDataRule(models.Model):
    """Quality rules for product master-data fields.

    One record per validated field (barcode, internal reference,
    lot/batch). Defines the minimum length, an optional regex pattern,
    and an optional checksum check. The data-completeness report and
    the bonus-scorecard KPI read these rules so the definition of
    "complete" can be tightened over time without code changes.
    """
    _name = 'pharmacy.data.rule'
    _description = 'Pharmacy Data Quality Rule'
    _order = 'field_key'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    field_key = fields.Selection(
        selection=[
            ('barcode', 'Product Barcode'),
            ('default_code', 'Internal Reference'),
            ('lot_name', 'Lot / Batch Number'),
        ], string='Field', required=True, index=True)
    active = fields.Boolean(string='Active', default=True,
                            help='When inactive the rule is ignored; only '
                                 'a non-empty check remains.')
    min_length = fields.Integer(
        string='Minimum Length', default=0,
        help='Values shorter than this are treated as invalid. '
             'Set 0 to disable.')
    regex_pattern = fields.Char(
        string='Regex Pattern',
        help='Optional Python regular expression. Values that do not '
             'match are treated as invalid. Leave empty to disable.')
    enforce_checksum = fields.Boolean(
        string='Enforce Barcode Checksum',
        help='For the barcode field only: validate that the value is a '
             'well-formed EAN-8, EAN-13, UPC-A or GTIN-14 with a correct '
             'check digit. Recommended only after the bulk of records '
             'have been cleaned.')
    description = fields.Text(string='Rule Description')

    _sql_constraints = [
        ('uniq_field_key',
         'unique(field_key)',
         'Only one rule per field is allowed.'),
    ]

    @api.depends('field_key')
    def _compute_name(self):
        labels = dict(self._fields['field_key'].selection)
        for rule in self:
            rule.name = labels.get(rule.field_key) or rule.field_key or ''

    @api.constrains('regex_pattern')
    def _check_regex(self):
        for rule in self:
            if not rule.regex_pattern:
                continue
            try:
                re.compile(rule.regex_pattern)
            except re.error as exc:
                raise ValidationError(_(
                    'Invalid regular expression: %s') % exc)

    @api.model
    def _get_rules(self):
        """Return a dict keyed by field_key for fast in-memory lookup."""
        rules = {}
        for rec in self.sudo().search([('active', '=', True)]):
            rules[rec.field_key] = {
                'min_length': rec.min_length or 0,
                'regex': rec.regex_pattern or '',
                'enforce_checksum': rec.enforce_checksum,
            }
        return rules

    @staticmethod
    def _gtin_checksum_ok(value):
        """Validate EAN-8, EAN-13, UPC-A or GTIN-14 check digit.

        All of these use the same mod-10 algorithm with alternating
        weights of 3 and 1 from the right. Values that are not all
        digits or not one of these accepted lengths fail.
        """
        if not value:
            return False
        digits = value.strip()
        if not digits.isdigit():
            return False
        if len(digits) not in (8, 12, 13, 14):
            return False
        body, check = digits[:-1], int(digits[-1])
        total = 0
        for i, ch in enumerate(reversed(body)):
            weight = 3 if i % 2 == 0 else 1
            total += int(ch) * weight
        expected = (10 - (total % 10)) % 10
        return expected == check

    @api.model
    def value_is_valid(self, field_key, value):
        """Check a single value against the active rule for its field.

        :returns: True when the value is non-empty *and* satisfies the
                  rule. False otherwise.
        """
        if value is None:
            return False
        text = str(value).strip()
        if not text:
            return False
        rules = self._get_rules()
        cfg = rules.get(field_key)
        if not cfg:
            # No active rule: presence is enough.
            return True
        if cfg['min_length'] and len(text) < cfg['min_length']:
            return False
        if cfg['regex']:
            try:
                if not re.match(cfg['regex'], text):
                    return False
            except re.error:
                # Misconfigured regex: fail closed (treat as invalid).
                return False
        if cfg['enforce_checksum'] and field_key == 'barcode':
            if not self._gtin_checksum_ok(text):
                return False
        return True

    def action_refresh_view(self):
        """Rebuild the data-completeness SQL view to apply rule changes.

        SQL views encode the active rules at view-creation time. When a
        rule changes, the view must be rebuilt for the dashboard and the
        bonus to reflect the change. Module upgrade does this; this
        button does it on demand.
        """
        self.env['report.pharmacy.data.completeness'].sudo().init()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Data Quality Rules',
                'message': 'Rules applied. Refresh the Data Completeness '
                           'dashboard to see the updated figures.',
                'type': 'success',
                'sticky': False,
            },
        }
