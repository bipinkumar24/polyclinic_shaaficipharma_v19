# -*- coding: utf-8 -*-
{
    'name': "Display Partner Phone on Partner Ledger Report",

    'summary': "this module extends partner ledger report to add phone number of selected partners",

    'description': """
            this module extends partner ledger report to add phone number of selected partners. 
    """,

    'author': "Medidod Consulting",
    'website': "https://www.mediodconsulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting/Accounting',
    'version': '19.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['account_reports'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        'views/account_partner_ledger_account_holder.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],

    "license": "OPL-1",

    'application': True,
    'price': 9.00,
    'currency': 'EUR',
    "images": ['static/description/Banner.png'],
}

