# -*- coding: utf-8 -*-
{
    'name': 'Shafic Clinic Performance',
    'version': '19.0.5.0.0',
    'summary': 'Treating physician on patient invoices + physician performance '
               'analysis (revenue by physician and service type).',
    'description': """
Shafic Clinic Performance
=========================
1. Adds a *treating physician* field to patient invoices, auto-filled from the
   linked clinical document (appointment / procedure / surgery / vaccination).
   ACS HMS core only stores ``ref_physician_id`` (the referring physician); the
   actual treating physician was never on the posted invoice.

2. Physician Performance analysis (this version): a read-only SQL-view report
   giving revenue per physician broken down by service type (Consultation,
   Procedure, Pharmacy, Lab, Radiology, ...), with volumes, paid vs outstanding,
   and ranking. Native pivot + graph + drill-down list, filterable by date and
   payment status. Service type is read from the product's hospital_product_type.
""",
    'author': 'Shafic Retail Pharmacy & Polyclinic',
    'category': 'Medical',
    'license': 'LGPL-3',
    'depends': ['account', 'acs_hms', 'acs_hms_cashier'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/physician_performance_views.xml',
        'views/prescription_performance_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
