# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResCardcommission(models.Model):
    _name = 'res.card.commission'
    _discrption = 'Card Commission'
    _inherit = ['pos.load.mixin']
    _rec_name = 'card_number'

    partner_id = fields.Many2one('res.partner', string='Partner Name')
    card_number = fields.Char(string="Card Number")
    percentage = fields.Float(string="Percentage")
    clinic_commis_record_count = fields.Integer(string="Clinic Record Count", compute="_clinic_commis_record_compute")
    registration_date = fields.Date(string="Registration Date", default=fields.Date.context_today)
    state = fields.Selection([('draft', 'Draft'),('confirmed', 'Confirmed')], default='draft', tracking=True)
    balance = fields.Float('Balance', compute="_compute_balance")
    company_id = fields.Many2one('res.company', ondelete='restrict', string='Company', default=lambda self: self.env.company)
    card_commission_payment = fields.Integer(string='Payment', compute="_payment_record_compute")
    filter_balance= fields.Float('Balance', compute="_compute_balance", store=True)

    def _load_pos_data_fields(cls, config_id):
        return ['card_number', 'percentage', 'partner_id', 'state']

    @api.depends('partner_id', 'company_id')
    def _compute_balance(self):
        # for rec in self:
        #     account_id = rec.company_id.commission_credit_account_id
        #     if account_id:
        #         move_line = self.env['account.move.line'].search(
        #             [('partner_id', '=', rec.partner_id.id),
        #             ('account_id', '=', account_id.id),
        #             ('move_id.state', '=', 'posted')
        #                 ])

        #         # total_credit = sum(move_lines.mapped('credit'))
        #         # total_debit = sum(move_lines.mapped('debit'))

        #         # balance = total_credit - total_debit

        #             balance = sum(move_line.mapped('balance')) if move_line else 00
        #             if balance:
        #                 if balance > 0:
        #                     rec.balance = balance
        #                 else:
        #                     rec.balance = balance * -1
        for rec in self:
            rec.balance = 0.0

            if not rec.partner_id or not rec.company_id.commission_credit_account_id:
                continue

            account = rec.company_id.commission_credit_account_id

            result = self.env['account.move.line'].read_group(
                domain=[
                    ('partner_id', '=', rec.partner_id.id),
                    ('account_id', '=', account.id),
                    ('move_id.state', '=', 'posted'),
                ],
                fields=['balance:sum'],
                groupby=[]
            )

            balance = result[0]['balance'] if result else 0.0
            rec.balance = abs(balance)
            rec.filter_balance = abs(balance)


    @api.depends('card_number', 'partner_id', 'partner_id.name')
    def _compute_display_name(self):
        for rec in self:
            name = rec.card_number or ''
            if rec.partner_id:
                name += ' - ' + rec.partner_id.name
            rec.display_name = name

    def _clinic_commis_record_compute(self):
        for rec in self:
            rec.clinic_commis_record_count = self.env['pos.card.commission'].search_count(
                [('card_number', '=', rec.card_number)])

    def _payment_record_compute(self):
        for rec in self:
            rec.card_commission_payment = self.env['account.payment'].search_count([('res_card_commission_id', '=', rec.id)])

    def action_view_pos_clinic_commission(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Card Commissio Record'),
            'res_model': 'pos.card.commission',
            'domain': [('card_number', '=', self.card_number)],
            'view_mode': 'list,kanban,form',
            'target': 'current'
        }

    def action_view_clinic_commission_payment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Card Commissio Payment'),
            'res_model': 'account.payment',
            'domain': [('res_card_commission_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'current'
        }

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_create_journal_entry(self):
        view_id = self.env.ref('do_pos_commission.action_card_commission_payment').id
        return {
            'name': 'POS Card Commission Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'commission.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context':{
                'default_partner_id': self.partner_id.id,
                'default_amount' : self.balance,
                'default_res_card_commission_id': self.id,
            }
        }