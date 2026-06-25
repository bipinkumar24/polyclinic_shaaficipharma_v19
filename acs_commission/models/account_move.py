# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    acs_commission_partner_ids = fields.Many2many("res.partner", "partner_move_line_commission_rel", "move_line_id", "partner_id", "Commission For")
    acs_no_commission = fields.Boolean("No Commission")


class AccountMove(models.Model):
    _inherit = "account.move"

    commission_partner_ids = fields.Many2many("res.partner", "partner_invoice_commission_rel", "invoice_id", "partner_id", "Commission For", compute="_compute_commission_partner_ids", store=True)
    commission_ids = fields.One2many('acs.commission', 'invoice_id', 'Sales Commission')
    commission_type = fields.Selection([
        ('automatic', 'Automatic'),
        ('fix_amount', 'On Fix Amount'),
    ], string='Commission Type', default='automatic', required=True)
    commission_created = fields.Boolean("Commission Finalized")
    commission_on = fields.Float('Commission On')

    @api.onchange('amount_untaxed')
    def onchange_total_amount(self):
        if self.company_id.commission_on_invoice_amount:
            self.commission_on = self.amount_untaxed

    @api.depends('physician_id', 'physician_id.partner_id')
    def _compute_commission_partner_ids(self):
        for move in self:
            if move.physician_id and move.physician_id.partner_id:
                move.commission_partner_ids = [(6, 0, [move.physician_id.partner_id.id])]
            else:
                move.commission_partner_ids = [(5, 0, 0)]

    # @api.onchange('invoice_user_id')
    # def onchange_acs_invoice_user(self):
    #     if self.invoice_user_id and self.invoice_user_id.provide_commission:
    #         self.commission_partner_ids = [(4, self.invoice_user_id.partner_id.id)]

    #ACS: call onchange to set inv user id in commission in case of inv creation from sale.
    # @api.model_create_multi
    # def create(self, vals_list):
    #     res = super().create(vals_list)
    #     for record in res:
    #         record._compute_commission_partner_ids()
    #     return res

    def create_partner_commission(self, partner, amount, commission_on, invoice_line=[]):
        Commission = self.env['acs.commission']
        commission_line = Commission.search([('partner_id','=',partner.id),('invoice_id','=',self.id)], limit=1)
        invoice_line_data = [(4, line_id) for line_id in invoice_line.ids] if invoice_line else []
        if commission_line:
            if amount:
                commission_line.write({
                    'commission_amount': amount,
                    'commission_on': commission_on,
                    'acs_invoice_line_ids': invoice_line_data,
                })
                commission_line.acs_update_amount_by_rules()
            else:
                commission_line.unlink()

        elif amount:
            Commission.create({
                'partner_id': partner.id,
                'commission_amount': amount,
                'commission_on': commission_on,
                'acs_invoice_line_ids': invoice_line_data,
                'invoice_id': self.id,
            })            

    def compute_partner_commission(self, partner):
        amount = commission_on = 0
        Rule = self.env['acs.commission.rule']
        lines = self.env['account.move.line']
        for line in self.invoice_line_ids.filtered(lambda l: l.product_id and not l.acs_no_commission):
            if (not line.acs_commission_partner_ids) or (partner.id in line.acs_commission_partner_ids.ids):
                matching_rule = False
                product_tmpl_id = line.product_id.product_tmpl_id.id
                product_categ_id = line.product_id.categ_id.id
                if partner.commission_rule_ids:
                    partner_commission_ids = partner.commission_rule_ids.ids
                    matching_rule = Rule.search([('id','in',partner_commission_ids),
                        ('product_id','=',product_tmpl_id)], limit=1)
                    if not matching_rule:
                        matching_rule = Rule.search([('id','in',partner_commission_ids),
                        ('product_category_id','=',product_categ_id)], limit=1)

                if not matching_rule and partner.commission_role_id:
                    role_commission_ids = partner.commission_role_id.commission_rule_ids.ids
                    matching_rule = Rule.search([('id','in', role_commission_ids),
                        ('product_id','=',product_tmpl_id)], limit=1)
                    if not matching_rule:
                        matching_rule = Rule.search([('id','in', role_commission_ids),
                        ('product_category_id','=',product_categ_id)], limit=1)

                if matching_rule:
                    if matching_rule.type == 'percentage':
                        amount += (matching_rule.percentage * line.price_subtotal)/100
                    elif matching_rule.type == 'amount':
                        amount += matching_rule.amount * line.quantity
                    commission_on += line.price_subtotal
                    lines |= line

                elif partner.commission_percentage:
                    amount += (partner.commission_percentage * line.price_subtotal)/100
                    commission_on += line.price_subtotal
                    lines |= line
            self.create_partner_commission(partner, amount, commission_on, lines)
        return amount

    def update_commission_values(self):
        Commission = self.env['acs.commission']
        for rec in self:
            if rec.commission_type=='automatic':
                for partner in rec.commission_partner_ids:
                    self.compute_partner_commission(partner)
            else:
                if rec.commission_on==0:
                    raise UserError(_("Please Set Amount to calculate Commission"))

                for partner in rec.commission_partner_ids:
                    amount = (partner.commission_percentage * self.commission_on)/100
                    self.create_partner_commission(partner, amount, self.commission_on, self.invoice_line_ids)

            #remove extra lines
            commission_line = Commission.search([('partner_id','not in',rec.commission_partner_ids.ids),('invoice_id','=',self.id)])
            commission_line.sudo().unlink()

    def finalize_commission(self):
        for rec in self:
            if not rec.commission_ids:
                raise UserError(_("No Commission Lines to Finalize! Please create them first."))
            rec.commission_created = True
            rec.commission_ids.action_done()

    def action_post(self):
        for rec in self:
            if rec.commission_partner_ids:
                if not rec.commission_ids:
                    rec.update_commission_values()
                if rec.commission_ids and not rec.commission_created:
                    rec.finalize_commission()
        return super(AccountMove, self).action_post()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: