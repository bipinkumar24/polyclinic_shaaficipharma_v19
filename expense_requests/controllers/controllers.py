# -*- coding: utf-8 -*-
# from odoo import http


# class ExpenseRequests(http.Controller):
#     @http.route('/expense_requests/expense_requests', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/expense_requests/expense_requests/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('expense_requests.listing', {
#             'root': '/expense_requests/expense_requests',
#             'objects': http.request.env['expense_requests.expense_requests'].search([]),
#         })

#     @http.route('/expense_requests/expense_requests/objects/<model("expense_requests.expense_requests"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('expense_requests.object', {
#             'object': obj
#         })
