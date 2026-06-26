# -*- coding: utf-8 -*-
{
    'name': 'POS Stock No Negative',
    'version': '19.0.1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Prevents overselling in POS — validates stock against the selected location qty.',
    'description': """
        Blocks adding or changing qty in POS when it would exceed the available stock
        in the configured stock location. Works together with pos_load_product_location
        to use the same location setting and loaded stock.quant data.
    """,
    'author': 'Techvaria',
    'company': 'Techvaria',
    'maintainer': 'Techvaria',
    'website': 'https://techvaria.com',
    'depends': ['point_of_sale', 'pos_load_product_location'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'ts_pos_stock_no_negative/static/src/**/*',
        ],
    },
    'images': ['static/description/screen.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
