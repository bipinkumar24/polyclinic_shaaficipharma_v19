# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    subscription_id = fields.Many2one("acs.subscription", "Subscription", ondelete="restrict")


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    subscription_id = fields.Many2one("acs.subscription", "Subscription", ondelete="restrict")


class ResPartner (models.Model):
    _inherit = "res.partner"

    def _do_count(self):
        for rec in self: 
            rec.subscription_count = len(rec.subscription_ids)

    subscription_ids = fields.One2many("acs.subscription", "partner_id", "Subscriptions")
    subscription_count = fields.Integer(string='# of Subscription', compute='_do_count', readonly=True)

    def action_view_subscriptions(self):
        subscriptions = self.subscription_ids
        action = self.env["ir.actions.actions"]._for_xml_id("acs_subscription.acs_subscription_action")
        if len(subscriptions)==1:
            action['views'] = [(self.env.ref('acs_subscription.acs_subscription_form_view').id, 'form')]
            action['res_id'] = subscriptions.ids[0]
        else:
            action['domain'] = [('id', 'in', subscriptions.ids)]

        action.update({'context': {'default_partner_id': self.id}})
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: