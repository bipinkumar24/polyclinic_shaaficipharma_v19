# -*- coding: utf-8 -*-
{
    'name': 'Shafic CEO Pulse',
    'version': '19.0.5.0.0',
    'summary': "One-screen morning pulse: profitable, leaking, honest — across "
               "clinic and pharmacy, with exception-first triage.",
    'description': """
Shafic CEO Pulse
================
A native Tier-1 executive dashboard for Shafic Retail Pharmacy & Polyclinic.

One screen, every morning, answering three questions: are we profitable, are
we leaking, are we honest? Seven tiles (gross margin after AVCO COGS, patients
seen + revenue/visit, chair utilization, cash variance, script capture,
insurance stuck, A-class stockouts), each with vs-yesterday / vs-last-week and
a 14-day trend, led by a clinical-style triage strip that surfaces what needs
attention first.

Every tile is computed defensively: a metric whose data source is not present
shows a clear "needs source" state instead of breaking the screen.
""",
    'author': 'Shafic Retail Pharmacy & Polyclinic',
    'category': 'Productivity/Dashboard',
    'license': 'LGPL-3',
    'depends': ['base_setup', 'account', 'stock', 'point_of_sale', 'acs_hms_cashier'],
    'data': [
        'security/pulse_security.xml',
        'security/ir.model.access.csv',
        'views/pulse_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'shafic_pulse/static/src/pulse.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
