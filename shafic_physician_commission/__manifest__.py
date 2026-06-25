# -*- coding: utf-8 -*-
{
    'name': 'Shafic Physician Commission',
    'version': '19.0.1.2.0',
    'summary': 'Per-physician commission on clinic-service revenue',
    'description': """
Shafic Physician Commission
============================
Computes physician commission per the clinic's rule:

  1. Take each physician's clinic-service revenue (posted, ex-tax
     invoices for their appointments, procedures and treatments).
  2. Deduct an allocated expense rate (default 45%).
  3. Pay the physician's own commission % on the remaining base.

Example: Dr Kaahiye 25% and Dr Ifrah 10% of the 55% base
(= 13.75% and 5.5% of revenue respectively).

Rates are configurable per physician; the expense rate is editable per
run. The report lists, per physician, revenue, expense, base, rate and
commission for the chosen period.
""",
    'author': 'Shafic Retail Pharmacy',
    'category': 'Accounting',
    'license': 'LGPL-3',
    'depends': [
        'acs_hms_base',
        'acs_hms',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/commission_views.xml',
    ],
    'post_init_hook': '_post_init_seed_rates',
    'installable': True,
    'application': False,
}
