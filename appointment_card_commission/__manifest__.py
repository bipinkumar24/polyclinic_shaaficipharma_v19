# -*- coding: utf-8 -*-

{
    'name': 'Appointment Card Commission',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add appointment card commission field on customer invoice.',
    'depends': [
        'acs_hms',
        'acs_commission',
        'do_pos_commission',
        'do_insurance_card_balance_system',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/pos_card_commission_views.xml',
        'views/hms_appointment_views.xml',
        'views/appointment_invoice_wizard_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
