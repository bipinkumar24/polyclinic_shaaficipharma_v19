# -*- coding: utf-8 -*-

{
    'name': 'Do Pos Commission',
    'version': '19.0.0.1',
    'category': 'pos',
    'summary': """""",
    'author': 'Do Incredible',
    'sequence': 15,
    'depends': ['base', 'point_of_sale', 'acs_commission'],
    'data': [
        'security/ir.model.access.csv',
        # 'security/groups.xml',
        'views/res_card_commission_views.xml',
        'views/pos_card_commission_views.xml',
        'views/res_company_view.xml',
        'views/res_config_settings_view.xml',
        'views/pos_order.xml',
        'views/res_partner.xml',
        'wizard/commission_payment_wizard.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'do_pos_commission/static/src/**/*',
        ],
    },
   
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
