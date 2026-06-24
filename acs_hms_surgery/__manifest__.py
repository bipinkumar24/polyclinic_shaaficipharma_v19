# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.
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
    'name': 'Medical Surgery',
    'category': 'Medical',
    'summary': 'Manage Medical Surgery related operations',
    'description': """
    Manage Medical Surgery related operations hospital management system medical ACS HMS
    """,
    'version': '19.0.1.0.0',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'www.almightycs.com',
    'license': 'OPL-1',
    'depends': ['acs_hms'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/digest_data.xml',
        'report/package_report.xml',
        'report/surgery_report.xml',
        'views/surgery_base.xml',
        'views/surgery_template_view.xml',
        'views/surgery_view.xml',
        'views/hms_base_view.xml',
        'views/package_view.xml',
        'views/res_config_settings_views.xml',
        'views/digest_view.xml',
        'views/menu_item.xml',
    ],
    'demo': [
        'demo/hms_demo.xml',
    ],
    'images': [
        'static/description/hms_surgery_almightycs_odoo_cover.jpg',
    ],
    'sequence': 1,
    'application': True,
    'price': 36,
    'currency': 'USD',
}
