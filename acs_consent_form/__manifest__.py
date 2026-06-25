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
    'name': 'Electronic Consent Form',
    'summary': """Electronic Consent Forms for Employees and Customers.""",
    'description': """
        Electronic Consent Forms for employees and customers.
    """,
    'version': '19.0.1.0.0',
    'category': 'Extra Addons',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'https://www.almightycs.com',
    'license': 'OPL-1',
    'depends': ["mail","portal"],
    'data' : [
        'security/security.xml',
        'security/ir.model.access.csv',
        'report/consent_report.xml',
        'data/data.xml',
        'data/mail_template.xml',
        'views/consent_form_view.xml',
        'views/portal_template.xml',
        'views/menu_item.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'images': [
        'static/description/odoo_acs_consent_form_almightycs.jpg',
    ],
    'installable': True,
    'application': True,
    'sequence': 1,
    'price': 66,
    'currency': 'USD',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: