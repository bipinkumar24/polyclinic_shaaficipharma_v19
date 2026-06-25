# models/pos_customer_activation.py  (Odoo 18)
from odoo import models, fields, api
from odoo.tools.translate import _
import logging

_logger = logging.getLogger(__name__)


class PosCustomerActivation(models.Model):
    _name = 'pos.customer.activation'
    _description = 'POS Customer Activation Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        required=True, ondelete='cascade', index=True,
    )
    credit_limit = fields.Monetary(
        string='Requested Credit Limit',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    requested_by = fields.Many2one(
        'res.users', string='Requested By',
        default=lambda self: self.env.uid, readonly=True,
    )
    approved_by = fields.Many2one(
        'res.users', string='Approved / Rejected By', readonly=True,
    )
    approval_date = fields.Datetime(string='Decision Date', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason')
    state = fields.Selection(
        [
            ('pending',   'Pending'),
            ('approved',  'Approved'),
            ('rejected',  'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending', string='Status',
        tracking=True, index=True,
    )

    @api.depends('partner_id', 'create_date')
    def _compute_display_name(self):
        for rec in self:
            date_str = rec.create_date.strftime('%Y-%m-%d') if rec.create_date else ''
            rec.display_name = f"POS Activation – {rec.partner_id.name or '?'} ({date_str})"

    # ── Role check ────────────────────────────────────────────────────────
    def _check_approver_rights(self, user):
        allowed = [
            'account.group_account_user',
            'account.group_account_manager',
            'base.group_system',
        ]
        advisor = self.env.ref('account.group_account_advisor', raise_if_not_found=False)
        if advisor:
            allowed.append('account.group_account_advisor')

        for xml_id in allowed:
            group = self.env.ref(xml_id, raise_if_not_found=False)
            if group and user in group.all_user_ids:
                return True
        return False

    # ── Approval / Rejection ──────────────────────────────────────────────
    def _do_approve(self, approver):
        self.ensure_one()
        self.write({
            'state': 'approved',
            'approved_by': approver.id,
            'approval_date': fields.Datetime.now(),
        })
        self.partner_id.sudo().write({
            'pos_activation_state': 'approved',
            'pos_is_active': True,
            'pos_approved_by': approver.id,
            'pos_approval_date': fields.Datetime.now(),
            'pos_rejection_reason': False,
        })
        self.partner_id.message_post(
            body=_('POS activation approved by %s. Customer is now visible in POS.') % approver.name,
            subtype_xmlid='mail.mt_note',
        )
        _logger.info('POS activation APPROVED for %s by %s', self.partner_id.name, approver.name)

    def _do_reject(self, approver, reason=''):
        self.ensure_one()
        self.write({
            'state': 'rejected',
            'approved_by': approver.id,
            'approval_date': fields.Datetime.now(),
            'rejection_reason': reason,
        })
        self.partner_id.sudo().write({
            'pos_activation_state': 'rejected',
            'pos_is_active': False,
            'pos_approved_by': approver.id,
            'pos_approval_date': fields.Datetime.now(),
            'pos_rejection_reason': reason,
        })
        self.partner_id.message_post(
            body=_('POS activation rejected by %s. Reason: %s') % (approver.name, reason or '—'),
            subtype_xmlid='mail.mt_note',
        )

    # ── Back-office button actions ────────────────────────────────────────
    def action_approve(self):
        for rec in self:
            if rec.state != 'pending':
                continue
            if not rec._check_approver_rights(self.env.user):
                raise models.ValidationError(
                    _('You need the Accountant role or above to approve.')
                )
            rec._do_approve(self.env.user)

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject – Enter Reason'),
            'res_model': 'pos.customer.activation.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_activation_id': self.id},
        }
