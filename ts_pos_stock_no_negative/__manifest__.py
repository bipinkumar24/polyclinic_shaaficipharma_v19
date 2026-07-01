# -*- coding: utf-8 -*-
#############################################################################
#
#    Techvaria Solutions Pvt. Ltd.
#
#    Copyright (C) 2025-Techvaria Solutions(<https://techvaria.com>)
#    Author: Techvaria Solutions Pvt. Ltd.(info@techvaria.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

{
    'name': 'POS Stock No Negative',
    'version': '19.0.1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Prevents overselling in POS by blocking product additions or quantity changes that exceed available stock levels.',
    'description': 'The POS Stock No Negative app helps prevent overselling in Odoo POS by validating product stock levels in real time. It restricts adding or updating quantities for products that exceed available stock, ensuring your POS always operates within true inventory limits.',
    'author': 'Techvaria',
    'company': 'Techvaria',
    'maintainer': 'Techvaria',
    'website': 'https://techvaria.com',
    # pos_load_product_location provides pos.config.stock_location_ids /
    # selected_stock_location_id and loads stock.quant + stock.location into
    # the POS, which this module's per-location negative-stock check needs.
    'depends': ['point_of_sale', 'pos_load_product_location'],
    'data': [
             'views/res_config_settings_views.xml'
             ],
    'assets': {
        'point_of_sale._assets_pos': [
            'ts_pos_stock_no_negative/static/src/**/*'
            ],
    },
    'images': [
        'static/description/screen.jpg',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
