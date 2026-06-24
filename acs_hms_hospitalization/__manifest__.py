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
    'name': 'Hospitalization (In-Patient - IPD)',
    'category': 'Medical',
    'summary': 'Manage your Hospital equipment and related process of Inpatient Registration, Surgery, Care, Discharge',
    'description': """
    Hospitalization is include Inpatient Registration, Surgery, Care, Discharge. Hospital related Flows. ACS HMS
    """,
    'license': 'OPL-1',
    'version': '19.0.1.0.0',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'www.almightycs.com',
    'live_test_url': 'https://www.youtube.com/watch?v=WDeqPLDHTd0',
    'depends': ['acs_hms', 'acs_hms_surgery'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/transfer_accommodation_view.xml',
        'wizard/acs_hospitalization_forecast_view.xml',
        'views/hospitalization_view.xml',
        'views/hospitalization_care_views.xml',
        'views/bed_view.xml',
        'views/ward_view.xml',
        'views/building_view.xml',
        'views/ot_view.xml',
        'views/hms_base_view.xml',
        'views/death_register.xml',
        'views/care_plan_template_view.xml',
        'views/res_config_settings_views.xml',
        'views/digest_view.xml',
        'report/report_hospital_discharge.xml',
        'report/report_visiting_pass.xml',
        'report/report_hospitalization_patient_card.xml',
        'report/ward_patient_list_report.xml',
        'report/report_hospitalization_forecast.xml',
        'report/report_death_register.xml',
        'data/sequence.xml',
        'data/hms_data.xml',
        'data/digest_data.xml',
        'views/menu_item.xml',
    ],
    'demo': [
        'demo/ward_demo.xml',
        'demo/bed_product_demo.xml',
        'demo/bed_demo.xml',
    ],
    'images': [
        'static/description/hms_hospitalization_almightycs_odoo_cover.jpg',
    ],
    'sequence': 1,
    'application': True,
    'price': 71,
    'currency': 'USD',
}