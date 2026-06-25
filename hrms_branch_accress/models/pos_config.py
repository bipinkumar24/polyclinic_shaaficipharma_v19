# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_branch_id = fields.Many2one(related="pos_config_id.branch_id", store=True, readonly=False)

class PosConfig(models.Model):
    _inherit = 'pos.config'

    branch_id = fields.Many2one('res.branch','Branch', store=True)

    def default_get(self, default_fields):
        res = super(PosConfig, self).default_get(default_fields)
        branch_id = False
        if self.env.context.get('branch_id'):
            branch_id = self.env.context.get('branch_id')
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        if 'branch_id' in default_fields:
            res.update({'branch_id': branch_id})
        return res

  


    