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
    'name': 'Dental Chart ( Odontology )',
    'version': '19.0.1.0.0',
    'summary': 'Dental Chart ( Odontology ) By AlmightyCS',
    'description': """
        Hospital Management System for Dental. Odontology management system for hospitals
        With this module you can manage Eye Patients acs hms almightycs dentist
    """,
    'category': 'Medical',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'https://www.almightycs.com',
    'license': 'OPL-1',
    'depends': ['acs_hms_dental'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/tooth_data.xml',
        'views/hms_dental_view.xml',
        'views/acs_hms_views.xml',
        'views/template.xml',
        'views/menu_item.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'acs_hms_dental_chart/static/src/scss/custom.scss',
            'acs_hms_dental_chart/static/src/js/popper.js',
            'acs_hms_dental_chart/static/src/js/dental_chart.js'
        ],
    },
    'images': [
        'static/description/acs_hms_dental_almightycs_cover.jpg',
    ],
    'installable': True,
    'application': True,
    'sequence': 1,
    'price': 201,
    'currency': 'USD',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: