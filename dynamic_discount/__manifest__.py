# -*- coding: utf-8 -*-
{
    "name": "Customized Discounts I Real-Time Pricing I Variable Discounts I Demand-Based Pricing I Tailored Discounts I Variable Rate Discounts I Adaptable Discounts I Market-Driven Discounts I Real-Time Discounting I Performance-Based Discounts I On-Demand Pricing",

    "summary": """Apply discount amount in percentage and amount for global discount in POS""",

    "description": """
        Apply discount amount in percentage and amount for global discount in POS
    """,

    "author": "Axiom World",
    "website": "https://axiomworld.net/",
    "maintainer": "Axiom World",
    "category": "Point of Sale",
    "version": "19.0.1.0.0",
    "license": "OPL-1",
    "depends": ["point_of_sale", "pos_discount", "base", "account"],
    "installable": True,
    "auto_install": False,
    "data": [
        'data/discount_product.xml',
        "views/res_config_settings_view.xml",
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'dynamic_discount/static/src/**/*',
        ],
    },
    "images": [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],
    "installable": True,
    "auto_install": False,
    "price": 35,
    "currency": "USD"
}
