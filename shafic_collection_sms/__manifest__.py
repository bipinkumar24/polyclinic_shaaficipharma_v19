# -*- coding: utf-8 -*-
{
    'name': 'Shafic Debt Collection SMS',
    'version': '19.0.1.6.0',
    'summary': 'Generate the month-end outstanding-balance SMS file for Golis '
               'upload, with a review-and-select screen.',
    'description': """
Debt Collection SMS
===================
Pulls every customer with an outstanding receivable balance straight from
Accounting, lets the collector review and deselect, then produces a CSV that
matches the existing Golis upload format exactly (Main Phone, Customer Name,
BALANCE). Removes the manual partner-ledger export and Excel retyping.

A month-end scheduled action can pre-build the list automatically so the
collector only reviews and generates.

The Golis integration today is file-upload only. A clearly marked hook
(action_send_direct) is in place so that direct one-click sending can be wired
in later if Golis provide a real send API.
""",
    'author': 'Shafic Retail',
    'license': 'LGPL-3',
    'category': 'Accounting',
    'depends': ['base', 'account'],
    'data': [
        'security/collection_sms_security.xml',
        'security/ir.model.access.csv',
        'data/collection_sms_data.xml',
        'views/collection_sms_views.xml',
        'views/res_partner_views.xml',
        'data/collection_bonus_data.xml',
        'views/collection_bonus_views.xml',
    ],
    'installable': True,
    'application': True,
}
