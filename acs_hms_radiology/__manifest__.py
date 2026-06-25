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
    'name': 'Hospital Radiology Management',
    'summary': 'Manage Radiology requests, Radiology tests, Invoicing and related history for hospital.',
    'description': """
        This module add functionality to manage Radiology flow. radiology management system
        Hospital Management lab tests radiology invoices radiology test results ACS HMS
    """,
    'version': '19.0.1.0.0',
    'category': 'Medical',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'https://www.almightycs.com',
    'live_test_url': 'https://youtu.be/md87kak6ztQ',
    'license': 'OPL-1',
    'depends': ['acs_hms','acs_radiology'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'report/report_acs_radiology_prescription.xml',
        'report/radiology_report.xml',
        'report/report_medical_advice.xml',

        'views/hms_base_view.xml',
        'views/radiology_view.xml',
    ],
    'images': [
        'static/description/hms_radiology_almightycs_cover.jpg',
    ],
    'installable': True,
    'application': True,
    'sequence': 1,
    'price': 16,
    'currency': 'USD',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: