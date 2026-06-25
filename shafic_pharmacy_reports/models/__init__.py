# -*- coding: utf-8 -*-
# Configuration / master data
from . import pharmacy_product_category
from . import pharmacy_branch
from . import pharmacy_config
from . import product_template
from . import res_partner

# Operational records
from . import prescription
from . import controlled_drug_log
from . import insurance_claim
from . import product_recall
from . import pharmacy_audit_log

# Odoo core extensions
from . import pos_order
from . import pos_session
from . import stock_lot

# Reporting models (SQL views)
from . import product_effective_cost
from . import report_sales
from . import report_product_sales
from . import report_category_sales
from . import report_branch_performance
from . import report_cashier_performance
from . import report_stock_position
from . import report_stock_valuation
from . import report_stock_card
from . import pharmacy_stock_status_wizard
from . import pharmacy_stock_card_wizard
from . import report_stock_movement
from . import report_reorder
from . import report_expiry
from . import report_prescription_sales
from . import report_insurance
from . import report_profitability
from . import report_supplier_performance
from . import report_customer
from . import report_pos_control

# Dashboard
from . import pharmacy_dashboard
from . import pharmacy_bonus_scorecard
from . import pharmacy_bonus_snapshot
from . import pharmacy_stock_value_daily
from . import pharmacy_expiry_exclusion
from . import report_data_completeness
from . import pharmacy_data_rule
from . import stock_picking
from . import pharmacy_expiry_action
from . import pharmacy_stock_count
from . import report_cost_price_anomaly
from . import pharmacy_cost_anomaly_snapshot
from . import pharmacy_auto_prepared_order
from . import product_product_pos

# Scheduled jobs
from . import pharmacy_cron
