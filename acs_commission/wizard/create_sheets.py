# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _


class AcsCommissionSheetWiz(models.TransientModel):
    _name = "acs.commission.sheet.wizard"
    _description = "Create Commission Sheets"

    date_from = fields.Date(required=True, default=fields.Date.today)
    date_to = fields.Date(required=True, default=fields.Date.today)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id, required=True)
    partner_ids = fields.Many2many('res.partner', 'res_partner_commission_sheet_wiz', 'wizard_id', 'sheet_id', string='Partners')
    all_partners = fields.Boolean("All Partners")

    def create_sheets(self):
        CommissionSheet = self.env['acs.commission.sheet']
        Partner = self.env['res.partner']
        if self.all_partners:
            partners = Partner.search([('provide_commission','=', True)])
        else:
            partners = self.partner_ids

        for partner in partners:
            sheet = CommissionSheet.create({
                'partner_id':  partner.id,
                'date_from':  self.date_from,
                'date_to': self.date_to,
                'user_id': self.user_id.id,
            })
            sheet.get_data()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: