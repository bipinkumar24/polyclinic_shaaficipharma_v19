# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


class AcsClaimSheet(models.Model):
    _name = 'acs.claim.sheet'
    _description = 'Claim Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('claim_line_ids','claim_line_ids.amount_total')
    def _amount_all(self):
        for record in self:
            amount_total = 0
            for line in record.claim_line_ids:
                amount_total += line.amount_total
            record.amount_total = amount_total

    name = fields.Char(string='Name', readonly=True, tracking=True,default='New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', copy=False, default='draft', tracking=True)
    insurance_company_id = fields.Many2one('hms.insurance.company', string='Insurance Company', index=True, required=True, tracking=True)
    date = fields.Date(string="Clam Date", required=True, default=fields.Date.today)
    date_from = fields.Date(required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date( required=True, 
        default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id, required=True, tracking=True)
    claim_line_ids = fields.One2many('account.move', 'claim_sheet_id', string='Lines')
    note = fields.Text("Note")
    company_id = fields.Many2one('res.company',
        string='Hospital', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id",
        string='Currency')
    amount_total = fields.Float(compute="_amount_all", string="Total")

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an record which is not draft or cancelled.'))
        return super(AcsClaimSheet, self).unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                seq_date = None
                if vals.get('date'):
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
                vals['name'] = self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code('acs.claim.sheet', sequence_date=seq_date) or _("New")
        return super().create(vals_list)

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    def get_data(self):
        self.claim_line_ids.write({'claim_sheet_id': False})
        claim_lines = self.env['account.move'].search([
            ('partner_id','=',self.insurance_company_id.partner_id.id),
            ('invoice_date','>=',self.date_from),
            ('invoice_date','<=',self.date_to),
            ('claim_sheet_id','=',False),
            ('move_type','=', 'out_invoice'),
            ('state','=','posted')])
        claim_lines.write({'claim_sheet_id': self.id})