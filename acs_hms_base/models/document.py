from odoo import api, fields, models ,_

class ACSDocument(models.Model):
    _name = 'acs.document.type'
    _description = 'Document Type'
    
    name = fields.Char(string="Document Type", required=True)
    description = fields.Text(string="Description", required=True)