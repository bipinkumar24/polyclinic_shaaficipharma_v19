{
    'name': 'Insurance Card Balance Management System',
    'version': '19.0.0.1',
    'summary': 'Hospital Management System for Aesthetic By AlmightyCS',
    'description': """
        Insurance Card Balance Management System
    """,
    'category': 'Medical',
    'author': 'Do Incredible',
    'website': 'http://doincredible.com',
    'license': 'OPL-1',
    'depends': ['acs_hms_base', 'acs_hms', 'acs_radiology', 'acs_hms_surgery'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_move.xml',
        'views/patient_views.xml',
        'views/appointment_views.xml',
        'views/radiology_request_views.xml',
        'views/hms_surgery_views.xml',
        'views/prescription_views.xml',
        'views/lab_request_views.xml',
        'views/acs_patient_procedure_views.xml',
        'wizard/create_invoice_wizard.xml',
    ],

    'installable': True,
    'application': True,
    'sequence': 2,
}