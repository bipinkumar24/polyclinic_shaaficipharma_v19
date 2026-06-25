# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.readonly
    def action_open_label_layout(self):
        if any(tmpl.type == 'service' for tmpl in self):
            raise ValidationError(
                _("Labels cannot be printed for products of service type"))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Labels',
            'res_model': 'odoo.leeno.direct.print.label.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('leeno_direct_print.view_leeno_direct_print_label_wizard_form').id,
            'target': 'new',
            'context': {
                'default_model': 'product.template',
                'active_ids': self.ids,
                'active_model': 'product.template',
            },
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.readonly
    def action_open_label_layout(self):
        if any(product.type == 'service' for product in self):
            raise ValidationError(
                _("Labels cannot be printed for products of service type"))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Labels',
            'res_model': 'odoo.leeno.direct.print.label.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('leeno_direct_print.view_leeno_direct_print_label_wizard_form').id,
            'target': 'new',
            'context': {
                'default_model': 'product.product',
                'active_ids': self.ids,
                'active_model': 'product.product',
            },
        }
