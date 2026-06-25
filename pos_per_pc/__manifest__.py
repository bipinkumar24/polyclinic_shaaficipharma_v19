# -*- coding: utf-8 -*-
{
    'name': 'POS Price/UOM Per Pc',
    'version': '19.0.1.0.0',
    'summary': 'Sell prescription products per piece in Point of Sale',
    'description': """
Adds "Sales Price Per Pc" and "UOM for Per Pc" fields on products. When a
prescription order is settled in the POS, products configured with these
fields are added using the per-piece price and unit of measure.
""",
    'category': 'Point of Sale',
    'author': 'Bipin Prajapati',
    'license': 'OPL-1',
    'depends': ['acs_hms_pharmacy_pos', 'bi_pos_multi_uom'],
    'data': [
        'views/product_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_per_pc/static/src/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
}
