# -*- coding: utf-8 -*-

{
    'name': 'DO Internal Account Journal',
    'category': 'POS',
    'author': 'Do Incredible',
    'license': 'OPL-1',
    'sequence': '10',
    'summary': 'Use a Do Internal Account Journal',
    'website': 'https://doincredible.com',
    'version': '19.0.0.1',
    'description': """
        Use a Do Internal Account Journal
    """,
    'depends': ['base','stock_account','branch'],
    'data': [
        "security/security_view.xml",
        "views/account_move_view.xml",
        "views/product_categ_view.xml",
        "views/stock_picking_view.xml",
    ],
    'installable': True,
    'application': True,
    'images': ['static/description/icon.png'],
    'live_test_url': '',
}