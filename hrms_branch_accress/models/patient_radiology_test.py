# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PatientRadiologyTest(models.Model):
    _inherit = "patient.radiology.test"


    @api.model
    def default_get(self, default_fields):
        res = super(PatientRadiologyTest, self).default_get(default_fields)
        if self.env.user.branch_id and 'branch_id' in default_fields:
            res.update({
                'branch_id': self.env.user.branch_id.id or False
            })
        return res

    branch_id = fields.Many2one('res.branch')

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_branch = self.branch_id
        user = self.env.user
        if selected_branch:
            if user.has_group('branch.group_multi_branch'):
                allowed_branch_ids = self.env.context.get(
                    'allowed_branch_ids', [])
                if selected_branch.id not in allowed_branch_ids:
                    raise UserError(_(
                        "Please select an active branch only. Other branches may cause data inconsistency.\n\n"
                        "If you wish to work in another branch, switch to it using the top-right menu."
                    ))
            else:
                if selected_branch != user.branch_id:
                    raise UserError(_(
                        "You are not allowed to switch branches.\n\n"
                        "Please use your assigned branch or contact an administrator."
                    ))

