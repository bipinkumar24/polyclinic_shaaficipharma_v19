# -*- coding: utf-8 -*-
{
    'name': "Expense Request",
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    'description': """
        Long description of module's purpose
    """,
    'author': "Bipin Prajapati",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '19.0.0.1',
    'license': 'AGPL-3',
    'depends': ['base','account','sale','hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'wizard/remark_view.xml',
        'views/account.xml',
        'views/approval_level_account_view.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
}
