{
    'name': 'Detailed Account Ledger Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Reporting',
    'summary': 'A detailed account ledger with HTML, PDF, and Excel outputs.',
    'description': """
        - Report wizard to select Account and Date Range.
        - Output selection for HTML, PDF, and Excel.
        - Displays Opening and Closing Balances.
        - Groups transactions by date with daily subtotals.
        - Custom HTML/PDF design with Ubuntu font.
        - Direct Excel report download with matching format.
    """,
    'author': 'Ayesha Siddika Suchi',
    'depends': ['account', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_ledger_wizard_view.xml',
        'report/report_templates.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'as_detailed_account_ledger_report/static/src/css/report_style.css',
        ],
    },
    'images': ['static/description/images/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 7,
    'currency': 'USD'

}
