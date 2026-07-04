{
    'name': 'Payment Request',
    'version': '19.0.5.0.0',
    'summary': 'Payment requests with approval, loan schedule, advance/overtime reports, bulk creation',
    'description': """
Payment Request Module for Odoo 19
====================================
Request types: Loan, Salary Advance, Overtime, Purchase, Expense, Other
Approval flow: Requester > Dept. Manager > Finance Officer > GM Approver

Loan: Full questionnaire, amortisation schedule, instalment tracking
Advance/Overtime: Dedicated reports, PDF slips, pivot/graph analysis
Bulk Requests: Create advances or overtime for entire department at once
Bill auto-generated on final approval for all request types
    """,
    'author': 'Custom',
    'category': 'Human Resources',
    'depends': ['base', 'mail', 'hr', 'account'],
    'data': [
        'security/payment_request_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/mail_template_data.xml',
        'wizard/payment_request_reject_wizard_view.xml',
        'wizard/bulk_request_wizard_view.xml',
        'views/payment_request_views.xml',
        'views/loan_instalment_views.xml',
        'views/advance_overtime_views.xml',
        'views/payment_request_menu.xml',
        'report/payment_request_report.xml',
        'report/loan_instalment_report.xml',
        'report/advance_overtime_report.xml',
        'report/payment_request_report_template.xml',
        'report/loan_instalment_report_template.xml',
        'report/advance_overtime_report_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'payment_request/static/src/css/payment_request.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
