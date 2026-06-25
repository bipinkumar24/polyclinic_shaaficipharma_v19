# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta


class AcsSubscription(models.Model):
    _name = 'acs.subscription'
    _description = "Service Subscription"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('res_model_id')
    def _data_count(self):
        Invoice = self.env['account.move']
        for rec in self:
            records = 0
            if rec.res_model_id and rec.res_model_id.model:
                records = self.env[rec.res_model_id.model].search_count([('subscription_id','=',rec.id)])
            rec.record_count = records
            rec.remaining_service = rec.allowed_no_service - records
            rec.invoice_count = Invoice.search_count([('subscription_id', '=', rec.id)])

    number = fields.Char(string='Number', required=True, readonly=True, default="New", tracking=True)
    name = fields.Char(string='Name', related="number", readonly=True, tracking=True, store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('done', 'Closed'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, default='draft', tracking=True)

    note = fields.Text('Description')
    partner_id = fields.Many2one('res.partner', string='Customer', ondelete="cascade", required=True)
    allowed_no_service = fields.Integer("Allowed No of Services")
    remaining_service = fields.Integer("Remaining No of Services", compute="_data_count")
    contract_id = fields.Many2one("acs.contract", string="Contract", required=True)
    product_id = fields.Many2one("product.product", related="contract_id.product_id", string="Product",readonly=True)
    start_date = fields.Datetime("Start Date", default=fields.Datetime.now)
    end_date = fields.Datetime("End Date", required=True, default=fields.Datetime.now)
    invoice_count = fields.Integer(string='# of Invoices', compute='_data_count', readonly=True)
    invoice_ids = fields.One2many("account.move", "subscription_id", string='Invoices', copy=False)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id)

    res_model_id = fields.Many2one('ir.model', related="contract_id.res_model_id", string='Model', readonly=True)
    record_count = fields.Integer(string='# of Operations', compute='_data_count', readonly=True)
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Company', default=lambda self: self.env.company)
    acs_type = fields.Selection([
        ('full', 'Full In Advance'),
        ('discount', 'Price-list Based Discount'),
    ], string='Offer Type', copy=False, default='full', tracking=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    active_subsription_ids = fields.Many2many('acs.subscription', 'acs_current_active_subscription_rel', 'current_subscription_id', 'subscription_id', 'Active Subsriptions')
    last_active_subsription_date = fields.Datetime("Active Subsriprion End Date")
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number', _("New")) == _("New"):
                seq_date = None
                if vals.get('start_date'):
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['start_date']))
                vals['number'] = self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code('acs.subscription', sequence_date=seq_date) or _("New")
        return super().create(vals_list)

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an record which is not draft or canceled.'))
        return super(AcsSubscription, self).unlink()

    def _compute_display_name(self):
        for record in self:
            name = " [%(number)s] %(name)s (%(count)s)" % {
                'number': record.number,
                'name': record.contract_id.name,
                'count': _('%g remaining out of %g') % (record.remaining_service or 0.0, record.allowed_no_service or 0.0)
            }
            record.display_name = name

    def action_confirm(self):
        self.state = 'active'

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'
    
    def get_active_subsriptions(self):
        return self.search([('contract_id','=',self.contract_id.id),('partner_id','=',self.partner_id.id),('state','=','active')])

    @api.onchange("contract_id", "partner_id")
    def onchange_contract_id(self):
        if self.contract_id:
            self.allowed_no_service = self.contract_id.no_service
            self.acs_type = self.contract_id.acs_type
            self.pricelist_id = self.contract_id.pricelist_id and self.contract_id.pricelist_id.id or False
            active_subsription_ids = self.get_active_subsriptions()
            if active_subsription_ids:
                self.active_subsription_ids = active_subsription_ids.ids
                self.last_active_subsription_date = active_subsription_ids[-1].end_date
                self.start_date = active_subsription_ids[-1].end_date

    @api.onchange("start_date","contract_id")
    def onchange_start_date(self):
        if self.start_date and self.contract_id:
            self.end_date = self.start_date + relativedelta(**{ f"{self.contract_id.validity_unit}s": self.contract_id.validity_interval })

    def action_view_related_records(self):
        record_ids = self.env[self.res_model_id.model].search([('subscription_id','=',self.id)])
        return {
            'name':'Records',
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': self.res_model_id.model,
            'target': 'current',
            'type': 'ir.actions.act_window',
            'domain': [('id','in', record_ids.ids)],
            'nodestroy': True,
        }

    def action_invoice_create(self):
        product_id = self.product_id
        if not product_id:
            raise UserError(_("Please Set proper contract first."))

        lines = [(0, 0, {
            'name': product_id.name + '\n' + 'Subscription No: ' + self.number,
            'product_id': product_id.id,
            'quantity' : 1,
            'price_unit' : self.contract_id.price or product_id.list_price,
            'product_uom_id': product_id.uom_id.id,
        })]
        
        move_id = self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'currency_id': self.company_id.currency_id.id,
            'invoice_line_ids': lines,
        })
        move_id.subscription_id = self.id
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = move_id.id
        return action

    def action_view_invoice(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        
        if len(self.invoice_ids) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = self.invoice_ids.id
            action['domain'] = []
        else:
            action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        
        return action
    #This is lazy option to close subscriptions
    @api.model
    def close_subscriptions(self):
        subscriptions = self.search([('state','=','active'),('end_date','<=',fields.Datetime.now())])
        for subscription in subscriptions:
            subscription.action_done()

        subscriptions = self.search([('state','=','active'),('end_date','>=',fields.Datetime.now())])
        for subscription in subscriptions:
            if subscription.remaining_service <= 0:
                subscription.action_done()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: