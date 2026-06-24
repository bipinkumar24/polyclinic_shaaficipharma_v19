# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"
    
    def acs_get_lab_data(self, invoice_id=False):
        for lab_request in self.hospitalization_id.request_ids.filtered(lambda lab_req: lab_req.invoice_id):
            lab_request.state = 'to_invoice'
            lab_request.invoice_id = False