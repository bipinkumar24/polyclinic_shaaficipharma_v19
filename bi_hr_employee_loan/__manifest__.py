# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Employee Loan Management in Odoo',
    'version': '19.0.0.1',
    'category': 'Human Resources',
    'summary': 'Apps for HR Employee Loan Management HR Loan request employee loans human resource loan for employee advance salary for employee Loan Request Approval Employee Loan Disbursement Loan Report Loan Proof Loan Policy Employee Loan by Payroll Loan Installments',
    'description': """
	Odoo Employee Loan Management System module
	
	Employee Loan Management
	Menus:
human resource loan for employee 
Loans
Loans/Loans
Loans/Loans/Loan Requests
Loans/Loans/Loan Requests to Approve
Loans/Loans/Loan Installments
Loans/Accounting
Loans/Accounting/Loans to Disburse
Loans/Configuration
Loans/Configuration/Loan Proofs
Loans/Configuration/Loan Types
Loans/Configuration/Loan Policies
Main Features:
employee loans 
advance salary for employee
Loan Request and Approval
Loan Disbursment by Accountant
Loan Report
Loan Proofs Setup
Loan Types Configuration
Loan Policy Configuration
Repayment of Loan by Payroll - Intergrated with Payroll System
Repayment of Loan by Cash/Bank
Disbursment using Cash/Bank or Payroll
Loan Installments and Booking Interest and Booking entry if repayment method = cash/bank
	 """,
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.in',
    "price": 39,
    "currency": 'EUR',
    'depends': ['base', 'hr', 'portal', 'utm', 'account', 'hr_payroll', 'hr_payroll_account'],
    'data': [
        'data/cron.xml',
        'data/sequnce_view.xml',
        'security/ir.model.access.csv',
        'security/groups.xml',
        'views/loan_proof_view.xml',
        'views/loan_request_view.xml',
        'views/loan_type_view.xml',
        'views/loan_policies_view.xml',
        'views/loan_installment_view.xml',
        'views/employee_views.xml',
        'views/account_payment_view.xml',
        'views/loan_rules.xml',
        'wizard/reject_request.xml',
        'wizard/loan_installment_wizard_view.xml',
        'wizard/indemnity_wizard_view.xml',
        'report/loan_report_action.xml',
        'report/loan_installment_templete.xml',
        'report/report_views.xml',
        'report/print_loan_report.xml',
        'report/indemnity_report_templete.xml',
        # 'report/payslip.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'live_test_url': 'https://youtu.be/rTW20wwm78U',
    "images": ["static/description/Banner.png"],
}
