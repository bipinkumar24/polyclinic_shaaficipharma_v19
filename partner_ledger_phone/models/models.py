# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class partner_ledger_phone(models.Model):
#     _name = 'partner_ledger_phone.partner_ledger_phone'
#     _description = 'partner_ledger_phone.partner_ledger_phone'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

