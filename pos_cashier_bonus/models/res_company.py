from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cash_diff_gain_account_id = fields.Many2one(
        'account.account', string='POS Cash Difference Gain Account',
        help="Account that POS session closings post cash overages to. "
             "Used to read each session's closing difference.")
    cash_diff_loss_account_id = fields.Many2one(
        'account.account', string='POS Cash Difference Loss Account',
        help="Account that POS session closings post cash shortages to. "
             "Used to read each session's closing difference.")
