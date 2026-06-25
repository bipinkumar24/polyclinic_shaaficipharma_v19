{
    'name': 'POS Cashier Sales Bonus',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Calculate cashier sales bonuses from POS sales against a monthly target.',
    'description': """
POS Cashier Sales Bonus
=======================
Pulls Point of Sale order data per cashier for a chosen period and computes
a sales-performance bonus from a shared allowance pool.

Bonus rule
----------
* Achievement %% = Actual POS Sales / Monthly Target
* Below the minimum threshold (default 70%%): no bonus.
* At or above the threshold: bonus = Achievement %% x Full Bonus, capped at the
  full bonus (100%% allocation) so the total never exceeds the allowance pool.
* Optional: scale beyond 100%% for over-achievement.
* Optional: redistribute the unused pool among cashiers who reached target.
""",
    'author': 'Salaam Group',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'hr', 'mail', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/pos_cashier_bonus_views.xml',
        'views/pos_session_closing_views.xml',
        'report/bonus_report.xml',
        'report/session_closing_report.xml',
    ],
    'installable': True,
    'application': False,
}
