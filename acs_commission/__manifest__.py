# -*- coding: utf-8 -*-
#╔══════════════════════════════════════════════════════════════════════╗
#║                                                                      ║
#║                  ╔═══╦╗       ╔╗  ╔╗     ╔═══╦═══╗                   ║
#║                  ║╔═╗║║       ║║ ╔╝╚╗    ║╔═╗║╔═╗║                   ║
#║                  ║║ ║║║╔╗╔╦╦══╣╚═╬╗╔╬╗ ╔╗║║ ╚╣╚══╗                   ║
#║                  ║╚═╝║║║╚╝╠╣╔╗║╔╗║║║║║ ║║║║ ╔╬══╗║                   ║
#║                  ║╔═╗║╚╣║║║║╚╝║║║║║╚╣╚═╝║║╚═╝║╚═╝║                   ║
#║                  ╚╝ ╚╩═╩╩╩╩╩═╗╠╝╚╝╚═╩═╗╔╝╚═══╩═══╝                   ║
#║                            ╔═╝║     ╔═╝║                             ║
#║                            ╚══╝     ╚══╝                             ║
#║                  SOFTWARE DEVELOPED AND SUPPORTED BY                 ║
#║                ALMIGHTY CONSULTING SOLUTIONS PVT. LTD.               ║
#║                      COPYRIGHT (C) 2016 - TODAY                      ║
#║                      https://www.almightycs.com                      ║
#║                                                                      ║
#╚══════════════════════════════════════════════════════════════════════╝
{
    'name': 'Partner Incentive / Commission Management',
    'category': 'Accouting',
    'summary': 'Option to give commission & payment to Customer, Referral, Employee and third party contact in system',
    'description': """
        Incentive for Employees Incentive Management
        application to manage user commission for different objects. AlmightyCS
    """,
    'version': '19.0.1.0.0',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'https://www.almightycs.com',
    'live_test_url': 'https://www.youtube.com/watch?v=A-CNUzJb5YY',
    'license': 'OPL-1',
    'depends': ['account','acs_hms_base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'wizard/create_commission_bill_views.xml',
        'wizard/create_sheets_view.xml',
        'reports/commission_sheet_report.xml',
        'views/commission_view.xml',
        'views/commission_sheet_view.xml',
        'views/partner_view.xml',
        'views/res_config_settings_views.xml',
        'views/account_view.xml',
        'views/menu_item.xml',
    ],
    'images': [
        'static/description/acs_commission_almightycs_cover.jpg',
    ],
    'installable': True,
    'application': True,
    'sequence': 1,
    'price': 36,
    'currency': 'USD',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: