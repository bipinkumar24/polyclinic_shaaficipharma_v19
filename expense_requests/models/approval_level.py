# -*- coding: utf-8 -*-

from odoo import api, models, fields, _

class ApprovalLevel(models.Model):
    _name = 'approval.level.account'
    _description = 'Approval Level CRM'
    _order = 'level'

    name = fields.Char('Name')
    display_message = fields.Html('Display Message')
    level = fields.Integer('Level')
    is_last_approval = fields.Boolean('Is Last')
    is_reject = fields.Boolean('Is Reject')
    approval_user_ids = fields.Many2many('res.users', string='Approval User')
    is_customer_doc_required = fields.Boolean('Is Customer Doc Required')
    fields_ids = fields.Many2many('ir.model.fields', string='Required Fields')
    is_send_email = fields.Boolean('Is Send Email')
    email_template_id = fields.Many2one('mail.template', string="Mail Template")
    maximum_amount = fields.Float("Amount")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):        
        # total = self.env.context.get('amount_total', 0)
        is_reject = self.env.context.get('rejected', False)
        if domain is None:
            domain = []
        else:
            domain = domain.copy()
        if is_reject:
            domain += [('is_reject', '=', True)]
        return super(ApprovalLevel, self).search_read(domain, fields, offset, limit, order)

class RemarksRefund(models.Model):
    _name = 'remarks.approval.account'
    _description = 'Approval Remarks CRM'
    _order = 'remark_datettime desc'

    move_id = fields.Many2one('account.move', string='Customer Onboarding')
    name = fields.Char('Remarks')
    user_id = fields.Many2one('res.users', string='User')
    remark_datettime = fields.Datetime(string='Remark Datetime')
    from_stage_id = fields.Many2one('approval.level.account', string='From Stage', required=False)
    to_stage_id = fields.Many2one('approval.level.account', string='To Stage')
    consumed_hours = fields.Char(string='Consumed Time')
    remark_type = fields.Selection([('approve', 'Approved'), ('previous', 'Previous'), ('reject', 'Reject')])
