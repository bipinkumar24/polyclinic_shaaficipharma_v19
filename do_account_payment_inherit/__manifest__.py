# -*- coding: utf-8 -*-

{
    'name': 'DO Account Payment Inherit',
    'category': 'Account',
    'author': 'Do Incredible',
    'license': 'OPL-1',
    'sequence': '10',
    'summary': 'Use Account Payment',
    'website': 'https://doincredible.com',
    'version': '19.0.0.1',
    'description': """
        Use a Account Payment
    """,
    'depends': ['base', 'account'],
    'data': [
        "views/account_account_views.xml",
        "views/account_payment_views.xml",
    ],
    'installable': True,
    'application': True,
    # 'images': ['static/description/icon.png'],
    'live_test_url': '',
}