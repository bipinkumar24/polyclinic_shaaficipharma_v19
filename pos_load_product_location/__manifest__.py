# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2024 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{
    "name": "POS Load Product Location",
    "version": "19.0.1.2",
    "license": "OPL-1",
    "author": "Kanak Infosystems LLP.",
    "website": "https://www.kanakinfosystems.com",
    "category": "Point of Sale",
    "summary": "Load only products available in the selected stock location into POS.",
    "description": """
        This module is used to load only the current stock of stock location in POS,
        whose stock location to be selected in POS Settings.
        ================================================================================================================================
        """,
    "depends": ["point_of_sale"],
    "data": [
        "views/res_config_settings.xml",
    ],
    "assets": {},
    "images": ["static/description/banner.jpg"],
    "installable": True,
    "price": 35,
    "currency": "EUR",
}
