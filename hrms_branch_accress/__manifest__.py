{
    'name': 'HRMS Multiple Branch Accress',
    'version': '19.0.1.0.0',
    'summary': 'HRMS Multiple Branch Accress',
    'description': """
        HRMS Multiple Branch 1
    """,
    'category': 'HRMS',
    'author': 'Do Incredible',
    'website': 'http://doincredible.com',
    'license': 'OPL-1',
    'depends': ['acs_hms', 'acs_radiology', 'acs_laboratory', 'branch', 'point_of_sale', 'acs_hms_laboratory'],
    'data': [
        'security/security.xml',
        'views/appointment_views.xml',
        'views/radiology_request_views.xml',
        'views/lab_request_views.xml',
        'views/patient_radiology_test_views.xml',
        'views/hms_treatment_views.xml',
        'views/pos_config_views.xml',
    ],

    'installable': True,
    'application': True,
    'sequence': 2,
}