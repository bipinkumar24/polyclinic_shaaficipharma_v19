# -*- coding: utf-8 -*-
{
    'name': 'Shafic Prescription Handoff',
    'version': '19.0.2.0.0',
    'summary': 'Pharmacy worklist + QR scan-to-POS of clinic prescriptions',
    'description': """
Shafic Prescription Handoff
===========================
Surfaces confirmed clinic prescriptions (acs_hms) to the pharmacy as a
"Pending Prescriptions" worklist so scripts get filled at your own
counter instead of walking out on paper.

* Worklist of confirmed, not-yet-dispensed prescriptions with patient,
  prescriber, medicines and quantities.
* Estimated sale value priced per dispensing unit (e.g. per capsule),
  converted natively from each product's unit of measure \u2014 so a
  30-capsule script of a box-stocked product shows its true value.
* Membership tier shown per patient (when shafic_membership is present)
  so the cashier knows to apply the member discount.
* Mark Dispensed clears a script from the queue; the pharmacy never
  edits clinical data (dispensing flags are written through a controlled
  action).
* Printable handoff slip carrying only the patient name and prescription
  number with a QR code (no medicines on the paper).
* POS "Prescription" button: scan or type the number, preview the
  medicines, then add them to the order priced per dispensing unit. The
  prescription is marked dispensed automatically once the order is paid.
""",
    'author': 'Shafic Retail Pharmacy',
    'category': 'Point of Sale',
    'license': 'LGPL-3',
    'depends': [
        'acs_hms_base',
        'acs_hms',
        'point_of_sale',
        'acs_hms_pharmacy_pos',
        'uom',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/rx_worklist_views.xml',
        'report/rx_slip_report.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'shafic_rx_worklist/static/src/app/rx_scan_popup.js',
            'shafic_rx_worklist/static/src/app/rx_scan_popup.xml',
            'shafic_rx_worklist/static/src/app/rx_pos_store.js',
            'shafic_rx_worklist/static/src/app/rx_product_screen.js',
            'shafic_rx_worklist/static/src/app/rx_control_button.js',
            'shafic_rx_worklist/static/src/app/rx_control_button.xml',
        ],
    },
    'installable': True,
    'application': False,
}
