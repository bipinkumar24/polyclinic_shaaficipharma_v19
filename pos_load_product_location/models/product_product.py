# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2024 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_data_domain(self, data, config):
        """
        Filter products loaded into POS to only those with stock
        in the configured location.

        v19 server-side equivalent of the v15 JS PosDB.add_products filter.
        """
        base_domain = super()._load_pos_data_domain(data, config)

        if not config.stock_location_id:
            return base_domain

        # Find templates that have available quants at the configured location
        templates = self.search(base_domain)
        quants = self.env['stock.quant'].search([
            ('location_id', 'child_of', config.stock_location_id.id),
            ('quantity', '>', 0),
            ('product_id.product_tmpl_id', 'in', templates.ids),
        ])
        valid_ids = quants.mapped('product_id.product_tmpl_id').ids

        if not valid_ids:
            return base_domain  # No quants found → don't hide all products

        return [('id', 'in', valid_ids)]