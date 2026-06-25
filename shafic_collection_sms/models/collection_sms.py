# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
from collections import Counter
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

DEFAULT_MESSAGE = (
    "Mudane/Marwo {Customer Name}, hadhaaga aad ku leedahay Shafic Pharmacy "
    "waa ${BALANCE}. Fadlan iska bixi. Mahadsanid."
)


def normalize_somali_phone(raw):
    """Return a local Somali number (no country code), matching the existing
    Golis upload format, or False if nothing usable. Shared by the batch and
    line models so editing a phone in the UI uses the same rule as loading."""
    if not raw:
        return False
    digits = re.sub(r'\D', '', raw)
    if not digits:
        return False
    if digits.startswith('00252'):
        digits = digits[5:]
    elif digits.startswith('252'):
        digits = digits[3:]
    digits = digits.lstrip('0')
    return digits or False


def format_balance(value):
    """Plain number, max two decimals, trailing zeros stripped:
    26.35 -> '26.35', 150 -> '150', 6.8 -> '6.8'."""
    s = '%.2f' % (value or 0.0)
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s


class CollectionSmsBatch(models.Model):
    _name = 'collection.sms.batch'
    _description = 'Debt Collection SMS Batch'
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    company_id = fields.Many2one(
        'res.company', string='Branch / Company', required=True,
        default=lambda self: self.env.company,
    )
    date = fields.Date(
        string='Statement Date', required=True,
        default=fields.Date.context_today,
        help="Outstanding balances are read as of now; this date simply "
             "labels the run.",
    )
    min_balance = fields.Float(
        string='Minimum Balance', default=0.0,
        help="Only customers whose outstanding balance is strictly greater "
             "than this value are loaded. 0 = everyone who owes anything.",
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('generated', 'File Generated'),
         ('sent', 'Sent')],
        default='draft', string='Status', copy=False,
    )
    line_ids = fields.One2many(
        'collection.sms.line', 'batch_id', string='Customers',
    )
    line_count = fields.Integer(compute='_compute_counts', string='Total Customers')
    included_count = fields.Integer(compute='_compute_counts', string='Selected to Send')
    invalid_count = fields.Integer(compute='_compute_counts', string='Missing / Invalid Phone')
    duplicate_count = fields.Integer(compute='_compute_counts', string='Duplicate Numbers')
    total_balance = fields.Monetary(compute='_compute_counts', string='Total Outstanding')
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    file_data = fields.Binary(string='SMS File', readonly=True, copy=False, attachment=True)
    file_name = fields.Char(string='File Name', readonly=True, copy=False)

    message_template = fields.Char(
        string='Message to paste in Golis', default=DEFAULT_MESSAGE,
        help="Type this in the Golis 'Message' box. Insert {Customer Name} and "
             "{BALANCE} using the portal's 'Select Merge Field' dropdown so each "
             "client gets their own name and balance.",
    )

    sent_date = fields.Datetime(string='Sent On', readonly=True, copy=False)
    sent_uid = fields.Many2one('res.users', string='Sent By', readonly=True, copy=False)

    note = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('collection.sms.batch')
                vals['name'] = seq or _('New')
        return super().create(vals_list)

    @api.depends('line_ids', 'line_ids.include', 'line_ids.has_valid_phone',
                 'line_ids.balance', 'line_ids.duplicate_phone')
    def _compute_counts(self):
        for batch in self:
            lines = batch.line_ids
            sendable = lines.filtered(lambda l: l.include and l.has_valid_phone)
            batch.line_count = len(lines)
            batch.included_count = len(sendable)
            batch.invalid_count = len(lines.filtered(lambda l: not l.has_valid_phone))
            batch.duplicate_count = len(lines.filtered('duplicate_phone'))
            batch.total_balance = sum(sendable.mapped('balance'))

    # ------------------------------------------------------------------
    # Helpers (thin wrappers around the shared functions)
    # ------------------------------------------------------------------
    @api.model
    def _normalize_phone(self, raw):
        return normalize_somali_phone(raw)

    @api.model
    def _format_balance(self, value):
        return format_balance(value)

    def _excluded_partner_ids(self):
        """Partners that must never receive a collection SMS: the company's own
        contacts (branches)."""
        return self.env['res.company'].search([]).mapped('partner_id').ids

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_load_customers(self):
        self.ensure_one()
        self.line_ids.unlink()
        company = self.company_id
        AML = self.env['account.move.line'].with_company(company)
        domain = [
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('company_id', '=', company.id),
            ('reconciled', '=', False),
            ('partner_id', '!=', False),
            ('partner_id.collection_sms_exclude', '=', False),
            ('partner_id', 'not in', self._excluded_partner_ids()),
        ]
        groups = AML._read_group(
            domain,
            groupby=['partner_id'],
            aggregates=['amount_residual:sum'],
        )
        rows = []
        for partner, residual in groups:
            balance = residual or 0.0
            if balance <= self.min_balance:
                continue
            normalized = normalize_somali_phone(partner.mobile or partner.phone or '')
            rows.append({
                'partner_id': partner.id,
                'customer_name': partner.name or '',
                'phone': normalized or '',
                'balance': balance,
                'has_valid_phone': bool(normalized),
                'include': bool(normalized),
            })
        if not rows:
            raise UserError(_(
                "No customers with an outstanding balance above %s were found "
                "for %s."
            ) % (format_balance(self.min_balance), company.name))
        # flag duplicate phone numbers so they can be reviewed
        phone_counts = Counter(r['phone'] for r in rows if r['phone'])
        for r in rows:
            r['duplicate_phone'] = bool(r['phone'] and phone_counts[r['phone']] > 1)
        # sort by phone to mirror the existing upload ordering
        rows.sort(key=lambda r: r['phone'])
        self.line_ids = [(0, 0, r) for r in rows]
        self.state = 'draft'
        self.file_data = False
        self.file_name = False
        return True

    def action_generate_file(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda l: l.include and l.has_valid_phone)
        if not lines:
            raise UserError(_(
                "There are no selected customers with a valid phone number to "
                "write to the file."
            ))
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['Main Phone', 'Customer Name', 'BALANCE'])
        for line in lines.sorted(key=lambda l: l.phone):
            writer.writerow([
                line.phone,
                line.customer_name,
                format_balance(line.balance),
            ])
        content = buf.getvalue().encode('utf-8-sig')
        self.file_data = base64.b64encode(content)
        self.file_name = '%s Dayn.csv' % (self.company_id.name or 'Collection')
        self.state = 'generated'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('File ready'),
                'message': _('%d customers written. Download the file below and '
                             'upload it to Golis.') % len(lines),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_mark_sent(self):
        for batch in self:
            if batch.state != 'generated':
                raise UserError(_(
                    "Generate the file before marking the batch as sent."
                ))
            batch.write({
                'state': 'sent',
                'sent_date': fields.Datetime.now(),
                'sent_uid': self.env.uid,
            })
        return True

    def action_reset(self):
        for batch in self:
            batch.write({
                'state': 'draft',
                'file_data': False,
                'file_name': False,
                'sent_date': False,
                'sent_uid': False,
            })
        return True

    # ------------------------------------------------------------------
    # Future direct-send hook (Golis API) -- file-upload only for now
    # ------------------------------------------------------------------
    def action_send_direct(self):
        """Placeholder for direct Golis API sending.

        Golis currently accept an uploaded file only (with the message and
        merge fields entered in their portal). If they ever provide a real send
        API, wire it here using each line's `message` field as the SMS body.
        """
        raise UserError(_(
            "Direct sending is not configured yet.\n\n"
            "Golis currently accept an uploaded file only. Use 'Generate File', "
            "upload it to the Golis portal, choose the phone column and insert "
            "the merge fields, then Send.\n\n"
            "Once Golis provide an SMS send API, one-click direct sending can be "
            "enabled here."
        ))

    # ------------------------------------------------------------------
    # Month-end scheduled action
    # ------------------------------------------------------------------
    @api.model
    def _cron_prepare_month_end(self):
        """On the last day of the month, create a draft batch per company and
        load its debtors so the collector only has to review and generate."""
        today = fields.Date.context_today(self)
        if (today + timedelta(days=1)).month == today.month:
            return True  # not the last day of the month yet
        for company in self.env['res.company'].search([]):
            batch = self.with_company(company).create({
                'company_id': company.id,
                'date': today,
            })
            try:
                batch.action_load_customers()
            except UserError:
                batch.unlink()  # no debtors for this company this month
        return True


class CollectionSmsLine(models.Model):
    _name = 'collection.sms.line'
    _description = 'Debt Collection SMS Line'
    _order = 'phone'

    batch_id = fields.Many2one(
        'collection.sms.batch', required=True, ondelete='cascade',
    )
    company_id = fields.Many2one(related='batch_id.company_id', store=True)
    currency_id = fields.Many2one(related='batch_id.currency_id')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    customer_name = fields.Char(string='Customer Name', required=True)
    phone = fields.Char(string='Main Phone')
    balance = fields.Monetary(string='Balance', currency_field='currency_id')
    has_valid_phone = fields.Boolean(string='Valid Phone', default=True)
    duplicate_phone = fields.Boolean(string='Duplicate Number', default=False)
    include = fields.Boolean(string='Send', default=True)
    message = fields.Char(
        string='Message Preview', compute='_compute_message', store=False,
        help="What this client would receive once name and balance are merged "
             "in the Golis portal. For reference / future direct sending.",
    )

    @api.depends('customer_name', 'balance')
    def _compute_message(self):
        for line in self:
            bal = format_balance(line.balance)
            line.message = (
                "Mudane/Marwo %s, hadhaaga aad ku leedahay Shafic Pharmacy waa "
                "$%s. Fadlan iska bixi. Mahadsanid." % (line.customer_name or '', bal)
            )

    @api.onchange('phone')
    def _onchange_phone(self):
        """If the collector fixes a number on a flagged row, re-validate and
        re-include it automatically (and normalise to local format)."""
        for line in self:
            norm = normalize_somali_phone(line.phone or '')
            line.has_valid_phone = bool(norm)
            if norm and line.phone != norm:
                line.phone = norm
            line.include = bool(norm)
