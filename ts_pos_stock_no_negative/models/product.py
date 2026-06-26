# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

# In Odoo 19 the _load_pos_data_fields signature uses (self, config)
# where config is the pos.config record (not config_id like in Odoo 16/17).
# The field is_storable is already loaded by Odoo 19's product.template
# (see odoo/addons/point_of_sale/models/product_template.py line 167).
# We only need to additionally load qty_available.


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        # qty_available: global ORM value; JS will override with location-specific qty from quants
        if 'qty_available' not in fields_list:
            fields_list.append('qty_available')
        return fields_list


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        if 'qty_available' not in fields_list:
            fields_list.append('qty_available')
        return fields_list
