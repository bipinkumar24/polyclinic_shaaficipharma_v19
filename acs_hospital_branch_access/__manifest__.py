# -*- coding: utf-8 -*-
{
    'name': 'ACS Hospital Branch Access',
    'version': '19.0.1.0.0',
    'summary': 'Branch-wise access control for ACS Hospital',
    'description': """
        ACS Hospital Branch Access
        ==========================
        This module provides branch-wise access control for ACS Hospital Management.
        Users can access records only for their assigned hospital branches.
    """,
    'category': 'Healthcare',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'acs_hms_vaccination',
        'acs_hms_cashier',
        'acs_hms_surgery'  # ACS Hospital Management module
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        "security/security_acess_view.xml",
        "views/prescription_order_view.xml",
        "views/acs_patient_procedure_view.xml",
        "wizard/paymnet_laboratry_view.xml",
        "views/hms_surgery_view.xml",
        "views/acs_vaccination_view.xml",
        "views/acs_hospitalization_view.xml",
        "views/acs_laboratory_request_view.xml",
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
