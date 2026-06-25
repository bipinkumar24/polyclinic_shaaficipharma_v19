# -*- coding: utf-8 -*-
{
    'name': 'Shaafici Appointment Receipt',
    'version': '19.0.1.0.0',
    'category': 'Healthcare',
    'summary': 'Custom QWeb receipt report for HMS appointments (Shaafici Poly Clinic)',
    'description': """
Shaafici Appointment Receipt
============================
Adds a custom PDF receipt for the hms.appointment model that matches the
Shaafici Poly Clinic receipt layout (company header, ref no, queue number,
patient details, doctor / department / service block, and amount summary).
    """,
    'author': 'Custom',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'account',
        'acs_hms',
    ],
    'data': [
        'reports/appointment_receipt_report.xml',
        'reports/appointment_receipt_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
