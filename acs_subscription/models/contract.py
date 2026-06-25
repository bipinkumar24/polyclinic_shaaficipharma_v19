# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError, UserError


class AcsContract(models.Model):
    _name = 'acs.contract'
    _description = "Service Contract"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _subscription_count(self):
        for rec in self: 
            rec.subscription_count = len(rec.subscription_ids.ids)

    name = fields.Char(string='Name', required=True, tracking=True)
    number = fields.Char(string='Number', required=True, readonly=True, default="New")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('done', 'Closed'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, default='draft', tracking=True)
    note = fields.Html('Description')
    product_id = fields.Many2one("product.product", "Product", required=True)
    price = fields.Integer(string='Price')
    no_service = fields.Integer("No of Services")
    subscription_ids = fields.One2many("acs.subscription", 'contract_id', string='Subscriptions', readonly=True, copy=False)
    subscription_count = fields.Integer(string='# of Subscription', compute='_subscription_count', readonly=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id)
    res_model_id = fields.Many2one('ir.model', string='Model', ondelete="cascade", required=True)
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Company', default=lambda self: self.env.company)
    acs_type = fields.Selection([
        ('full', 'Full In Advance'),
        ('discount', 'Price-list Based Discount'),
    ], string='Offer Type', copy=False, default='full', tracking=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If you change the pricelist, only newly added lines will be affected.")
    validity_interval = fields.Integer(string='Validity', default=1)
    validity_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='month')

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an record which is not draft.'))
        return super(AcsContract, self).unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number', _("New")) == _("New"):
                seq_date = None
                if vals.get('date'):
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
                vals['number'] = self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code('acs.contract', sequence_date=seq_date) or _("New")
        return super().create(vals_list)

    def action_confirm(self):
        self.state = 'active'

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    @api.onchange("product_id")
    def onchange_product_id(self):
        domain = {}
        if self.product_id:
            
            self.price = self.product_id.lst_price

    def action_view_subscriptions(self):
        subscriptions = self.subscription_ids
        action = self.env["ir.actions.actions"]._for_xml_id("acs_subscription.acs_subscription_action")
        if len(subscriptions) > 1:
            action['domain'] = [('id', 'in', subscriptions.ids)]
        elif len(subscriptions) == 1:
            action['views'] = [(self.env.ref('acs_subscription.acs_subscription_form_view').id, 'form')]
            action['res_id'] = subscriptions.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        action.update({'context': {'default_contract_id': self.id}})
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: