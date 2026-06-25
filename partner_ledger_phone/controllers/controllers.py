# -*- coding: utf-8 -*-
# from odoo import http


# class PartnerLedgerPhone(http.Controller):
#     @http.route('/partner_ledger_phone/partner_ledger_phone', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/partner_ledger_phone/partner_ledger_phone/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('partner_ledger_phone.listing', {
#             'root': '/partner_ledger_phone/partner_ledger_phone',
#             'objects': http.request.env['partner_ledger_phone.partner_ledger_phone'].search([]),
#         })

#     @http.route('/partner_ledger_phone/partner_ledger_phone/objects/<model("partner_ledger_phone.partner_ledger_phone"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('partner_ledger_phone.object', {
#             'object': obj
#         })

