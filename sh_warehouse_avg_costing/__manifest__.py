# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Average Costing Warehouse Wise",
    "author": "Softhealer Technologies",
    "license": "OPL-1",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "version": "19.0.0.0.7",
    "category": "Warehouse",
    "summary": "Average Costing Method Average Warehouse Wise Costing Method Warehouse Average Costing Calculate Stock Landed Cost On Average Costing Method Landed Cost Service Cost Manage Cost Price Warehouse Cost Price Product Costing Odoo Warehouse Based Costing Based Warehouse Costing Warehouse Wise Average Costing Inventory Costing Stock Costing Product Costing Landed Cost On Costing Method Manage Average Costing Warehouse Wise Manage Costing Warehouse Wise",
    "description": """Nowadays in this fast forwarding world most of businesses who have storable products, they have multiple warehouses at different place. So the problem is one product have different landed cost and some service cost and company need to maintain demand of products at multi warehouses. At the end company are get different cost price of that products in each warehouses, and that things you can not manage in odoo. But Don't worry here we have solution for that. Our this app will help to manage your average costing warehouse wise.""",
    "depends": ["purchase", "stock", 'sale_management', 'stock_landed_costs', 'stock_account'],
    "data": [
        "security/sh_warehouse_costing_groups.xml",
        "security/ir.model.access.csv",
        "views/product_product_views.xml",
        'views/stock_quantity_history_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_revaluation_views.xml',
    ],
    "images": ["static/description/background.png", ],
    "auto_install": False,
    "installable": True,
    "application": True,
    "price": 500,
    "currency": "EUR"
}
