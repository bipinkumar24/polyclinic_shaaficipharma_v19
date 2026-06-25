# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductCategory(models.Model):
    _inherit = "product.category"

    inter_company_account = fields.Many2one("account.account", "Internal Transfer Account", company_dependent=True,
        check_company=True,
        help="""When automated inventory valuation is enabled on a product, this account will hold the Internal Transfer account value of the products.""",)
