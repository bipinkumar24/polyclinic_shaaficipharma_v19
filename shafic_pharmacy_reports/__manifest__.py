# -*- coding: utf-8 -*-
{
    'name': 'Shafic Pharmacy POS Reporting & Analytics',
    'version': '19.0.1.15.1',
    'category': 'Point of Sale',
    'summary': 'Comprehensive Retail Pharmacy POS Reporting, Analytics & '
               'Compliance module for single and multi-branch operations.',
    'description': """
Shafic Pharmacy POS Reporting & Analytics
=========================================
Extends Odoo POS, Inventory, Purchase, Accounting and CRM to deliver
pharmacy-specific operational, financial, compliance and analytical reports.

Functional coverage
--------------------
* Sales reporting (daily/weekly/monthly, product, category, branch, cashier)
* Inventory & stock reporting (position, valuation, fast/slow/dead stock,
  reorder, batch/lot tracking)
* Expiry management (alert dashboard, expired stock, near-expiry, recall)
* Prescription & compliance (prescription sales, controlled drugs register,
  doctor analysis, insurance billing, audit trail)
* Profitability analytics (product/category margin, discount impact,
  supplier margin)
* Procurement & supplier reporting
* Customer & loyalty reporting
* Financial & POS control (Z-report, cash reconciliation, payment analysis)
* Executive dashboard (OWL)
* Optional advanced analytics layer (demand forecast, basket analysis)
""",
    'author': 'Shafic Retail',
    'website': 'https://www.shaficretail.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'loyalty',
        'stock',
        'sale',
        'purchase',
        'account',
        'contacts',
        'point_of_sale',
        'product_expiry',
    ],
    'data': [
        # Security
        'security/pharmacy_security.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        # Data
        'data/ir_sequence_data.xml',
        'data/pharmacy_category_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/report_paperformat_data.xml',
        'data/pharmacy_data_rule_data.xml',
        # Wizards
        'wizards/sales_report_wizard_views.xml',
        'wizards/stock_report_wizard_views.xml',
        'wizards/expiry_report_wizard_views.xml',
        # Views - core config
        'views/pharmacy_branch_views.xml',
        'views/pharmacy_config_views.xml',
        'views/pharmacy_product_category_views.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        # Views - operational records
        'views/prescription_views.xml',
        'views/controlled_drug_log_views.xml',
        'views/insurance_claim_views.xml',
        'views/product_recall_views.xml',
        'views/pharmacy_audit_log_views.xml',
        # Views - reports
        'views/report_sales_views.xml',
        'views/report_product_sales_views.xml',
        'views/report_category_sales_views.xml',
        'views/report_branch_performance_views.xml',
        'views/report_cashier_performance_views.xml',
        'views/report_stock_position_views.xml',
        'views/report_stock_valuation_views.xml',
        'views/report_stock_card_views.xml',
        'views/pharmacy_stock_status_wizard_views.xml',
        'views/pharmacy_stock_card_wizard_views.xml',
        'views/report_stock_movement_views.xml',
        'views/report_reorder_views.xml',
        'views/report_expiry_views.xml',
        'views/report_prescription_sales_views.xml',
        'views/report_insurance_views.xml',
        'views/report_profitability_views.xml',
        'views/report_supplier_performance_views.xml',
        'views/report_customer_views.xml',
        'views/report_pos_control_views.xml',
        # Dashboard
        'views/dashboard_views.xml',
        'views/pharmacy_bonus_snapshot_views.xml',
        'views/pharmacy_expiry_exclusion_views.xml',
        'views/report_data_completeness_views.xml',
        'views/pharmacy_data_rule_views.xml',
        'views/pharmacy_expiry_action_views.xml',
        'views/pharmacy_stock_count_views.xml',
        'views/report_cost_price_anomaly_views.xml',
        'views/pharmacy_cost_anomaly_snapshot_views.xml',
        'views/products_to_fix_views.xml',
        'views/pharmacy_auto_prepared_order_views.xml',
        'views/stock_picking_views.xml',
        # QWeb PDF reports
        'reports/report_actions.xml',
        'reports/report_z_report_template.xml',
        'reports/report_expiry_template.xml',
        'reports/report_controlled_drug_template.xml',
        'reports/report_prescription_template.xml',
        # Menus (last)
        'views/menus.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'shafic_pharmacy_reports/static/src/js/pos_prescription.js',
            'shafic_pharmacy_reports/static/src/js/pos_expiry_notification.js',
            'shafic_pharmacy_reports/static/src/js/pos_expiry_check.js',
            'shafic_pharmacy_reports/static/src/xml/pos_expiry_notification.xml',
            'shafic_pharmacy_reports/static/src/css/pos_expiry.css',
        ],
        'web.assets_backend': [
            'shafic_pharmacy_reports/static/src/css/dashboard.css',
            'shafic_pharmacy_reports/static/src/js/dashboard.js',
            'shafic_pharmacy_reports/static/src/xml/dashboard.xml',
            'shafic_pharmacy_reports/static/src/js/bonus_scorecard.js',
            'shafic_pharmacy_reports/static/src/xml/bonus_scorecard.xml',
            'shafic_pharmacy_reports/static/src/js/data_completeness.js',
            'shafic_pharmacy_reports/static/src/xml/data_completeness.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
