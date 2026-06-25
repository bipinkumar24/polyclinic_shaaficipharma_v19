# models/res_partner.py  (Odoo 18)
from odoo import models, fields, api
from odoo.tools.translate import _
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── POS Activation fields ──────────────────────────────────────────────
    pos_allow_in_pos = fields.Boolean(
        string='Allow in POS',
        default=False,
        tracking=True)
    pos_credit_limit = fields.Monetary(
        string='POS Credit Limit',
        currency_field='currency_id',
        default=0.0,
        tracking=True)
    pos_activation_state = fields.Selection(
        [
            ('not_requested', 'Not Requested'),
            ('pending',       'Pending Approval'),
            ('approved',      'Approved – Active in POS'),
            ('rejected',      'Rejected'),
        ],
        string='POS Activation Status',
        default='not_requested',
        readonly=True,
        tracking=True,
        index=True,
        copy=False,
    )
    pos_activation_id = fields.Many2one(
        'pos.customer.activation',
        string='Latest Activation Request',
        readonly=True,
        ondelete='set null',
        copy=False,
    )
    pos_approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True, copy=False,
    )
    pos_approval_date = fields.Datetime(
        string='Approval Date', readonly=True, copy=False,
    )
    pos_rejection_reason = fields.Text(
        string='Rejection Reason', readonly=True, copy=False,
    )
    pos_is_active = fields.Boolean(
        string='Active in POS (Approved)',
        compute='_compute_pos_is_active',
        store=True,
        index=True,
        copy=False,
    )

    @api.depends('pos_activation_state')
    def _compute_pos_is_active(self):
        for p in self:
            p.pos_is_active = (p.pos_activation_state == 'approved')

    # ── POS Data Loading – expose custom fields to the POS frontend ────────
    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        extra = [
            'pos_allow_in_pos',
            'pos_credit_limit',
            'pos_is_active',
            'pos_activation_state',
        ]
        for f in extra:
            if f not in fields_list:
                fields_list.append(f)
        return fields_list

    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = super()._load_pos_data_domain(data, config)
        domain.append(('pos_allow_in_pos', '=', True))
        return domain

    # ── Onchange warning ──────────────────────────────────────────────────
    @api.onchange('pos_allow_in_pos', 'pos_credit_limit')
    def _onchange_pos_activation_fields(self):
        if self.pos_allow_in_pos and self.pos_credit_limit > 0:
            if self.pos_activation_state not in ('approved',):
                return {
                    'warning': {
                        'title': _('Approval Required'),
                        'message': _(
                            'Saving will create an approval request. '
                            'This customer will appear in POS only after '
                            'an Accountant or above approves the request.'
                        ),
                    }
                }

    # ── Write override ────────────────────────────────────────────────────
    def write(self, vals):
        result = super().write(vals)
        if {'pos_allow_in_pos', 'pos_credit_limit'}.intersection(vals.keys()):
            for partner in self:
                partner._check_and_create_activation_request()
        return result

    def _check_and_create_activation_request(self):
        if (
            self.pos_allow_in_pos
            and self.pos_credit_limit > 0
            and self.pos_activation_state != 'approved'
        ):
            # Cancel existing pending requests
            self.env['pos.customer.activation'].search([
                ('partner_id', '=', self.id),
                ('state', '=', 'pending'),
            ]).write({'state': 'cancelled'})

            request = self.env['pos.customer.activation'].create({
                'partner_id': self.id,
                'credit_limit': self.pos_credit_limit,
                'requested_by': self.env.uid,
            })
            self.write({
                'pos_activation_state': 'pending',
                'pos_activation_id': request.id,
            })
            _logger.info(
                'POS activation request created for partner %s (id=%s)',
                self.name, request.id,
            )
        elif not self.pos_allow_in_pos and self.pos_activation_state == 'approved':
            self.write({
                'pos_activation_state': 'not_requested',
                'pos_is_active': False,
            })

    # ── JSON-RPC helpers (called from POS JS) ─────────────────────────────
    @api.model
    def get_pending_pos_activations(self):
        requests = self.env['pos.customer.activation'].search([
            ('state', '=', 'pending')
        ])
        return [{
            'id': r.id,
            'partner_id': r.partner_id.id,
            'partner_name': r.partner_id.name,
            'credit_limit': r.credit_limit,
            'requested_by': r.requested_by.name,
            'create_date': r.create_date.strftime('%Y-%m-%d %H:%M') if r.create_date else '',
            'currency_symbol': r.partner_id.currency_id.symbol or '$',
        } for r in requests]

    @api.model
    def approve_pos_activation(self, activation_id, login, password):
        activation = self.env['pos.customer.activation'].sudo().browse(activation_id)
        if not activation.exists() or activation.state != 'pending':
            return {'error': _('Activation request not found or already processed.')}

        try:
            auth_info = self.env['res.users'].sudo()._login(
                {'type': 'password', 'login': login, 'password': password},
                user_agent_env={},
            )
            uid = auth_info['uid']
        except Exception:
            return {'error': _('Invalid username or password.')}

        approver = self.env['res.users'].sudo().browse(uid)
        if not activation._check_approver_rights(approver):
            return {'error': _(
                '"%s" does not have the Accountant role or above.'
            ) % approver.name}

        activation.sudo()._do_approve(approver)
        return {
            'success': True,
            'approver_name': approver.name,
            'partner_name': activation.partner_id.name,
        }

    @api.model
    def reject_pos_activation(self, activation_id, login, password, reason=''):
        activation = self.env['pos.customer.activation'].sudo().browse(activation_id)
        if not activation.exists():
            return {'error': _('Activation request not found.')}

        try:
            auth_info = self.env['res.users'].sudo()._login(
                {'type': 'password', 'login': login, 'password': password},
                user_agent_env={},
            )
            uid = auth_info['uid']
        except Exception:
            return {'error': _('Invalid username or password.')}

        approver = self.env['res.users'].sudo().browse(uid)
        if not activation._check_approver_rights(approver):
            return {'error': _('Insufficient role.')}

        activation.sudo()._do_reject(approver, reason)
        return {'success': True}

    def action_pos_customer_activations(self):
        """Open activation requests linked to this partner."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('POS Activation Requests'),
            'res_model': 'pos.customer.activation',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
