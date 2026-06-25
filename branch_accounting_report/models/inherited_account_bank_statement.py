# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import time

class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    branch_id = fields.Many2one('res.branch')

    def _get_opening_balance(self, journal_id):
        curr_user_id = self.env['res.users'].browse(self.env.context.get('uid', False))
        last_bnk_stmt = self.search([('journal_id', '=', journal_id),('branch_id','=',curr_user_id.branch_id.id)], limit=1)
        if last_bnk_stmt:
            return last_bnk_stmt.balance_end
        return 0

    @api.model
    def default_get(self,fields):
        res = super(AccountBankStatement, self).default_get(fields)
        branch_id = False
        if self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id
        res.update({
            'branch_id' : branch_id
        })
        return res

