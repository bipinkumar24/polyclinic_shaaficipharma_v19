# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Employee Advance Salary Requests In Odoo',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'HR Advance Salary Request for Employee salary Advance Salary Request Approval Director Approval on employee Advance Salary Employee Payslip Advance Employee Advance Payslip Advance Salary for employee Requests Advance Salary for employee Salary approval',
    'description': """This app allows employee to request for advance salary,
	Employee Advance Salary Requests
This module allow employee to request for advance salary. 
Main Features:
Employee advance salary request
Set salary limit on job position
Department Manager Approval
HR Officer/Manager Approval
Director Approval
Integrated with accounting for payment
Integrated with HR Payroll / Employee Payslips
We have created Department Manager, Director groups under settings/users/groups to control whole process.

Workflow: Draft->Confirmed->Approved by Department->Approved by HR->Approved by Director->Paid->Done
Advance Salary for employee Requests 
Salary for employee Requests
Advance Salary for employee
hr Advance Salary for employee
hr Advance Salary for employee


Menus Available:

Employees/Advance Salary
Employees/Advance Salary/Advance Salary Requests
Employees/Advance Salary/Department Approvals
Employees/Advance Salary/Director Approvals
Employees/Advance Salary/HR Approvals
Invoicing/Purchases/Advance Salary Requests
Employee Advance Salary Requests
Under HR menu to request advance salary by employee (List view). Normal employee can see his/her on request.(Thanks to Security added in module) with multiple approval from the higher authority. Helps to generate a report about advance salary""",
    
	
	'author': 'BrowseInfo',
    "price": 10,
    "currency": 'EUR',
    'license': 'LGPL-3',
    'website': 'https://www.browseinfo.in',
    'depends': ['base','hr','hr_payroll','account','bi_hr_overtime_request','bi_hr_employee_loan'],
    'data': [
            'data/cron.xml',
            'security/groups.xml',
            'security/ir.model.access.csv',
            'views/advance_salary_view.xml',
            'views/inherite_hr_job_view.xml',
            'views/account_move_view.xml',
            'report/advance_salary_action.xml',
            'report/custom_advance_salary_report.xml',
            # 'views/salary_rule.xml',
            'report/report_views.xml',
            'wizard/advance_salary_wizard_view.xml',
            'report/advance_salary_report.xml'],
    'installable': True,
    'live_test_url':'https://youtu.be/lYzufOFLtZc',
    'auto_install': False,
    'application': True,
	"images":['static/description/Banner.png'],
}
