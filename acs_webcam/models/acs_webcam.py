# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class AcsWebcamMixin(models.AbstractModel):
    _name = "acs.webcam.mixin"
    _description = "ACS Webcam Mixin"

    def acs_open_website_url(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/acs/webcam/' + self._name + '/' + str(self.id),
            'target': 'self',
        }


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner','acs.webcam.mixin']

    def acs_webcam_return_action(self):
        self.ensure_one()
        return self.env.ref('base.action_partner_form').id


class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = ['res.users','acs.webcam.mixin']

    def acs_webcam_return_action(self):
        self.ensure_one()
        return self.env.ref('base.action_res_users').id
