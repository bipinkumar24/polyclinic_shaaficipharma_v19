# -*- coding: utf-8 -*-
{
    "name": "Stock Picking Cancel / Reverse / Revert",
    "version": "19.0.1.0.0",
    "author": "Your Company",
    "category": "Warehouse/Stock",
    "summary": "Cancel or reverse validated/ done stock pickings, delivery orders and incoming shipments.",
    "description": """
        Minimal module to cancel, reset to draft or reverse completed stock pickings (delivery orders / incoming shipments).
        Use this module to allow reverting pickings that were validated by mistake.
    """,
    "depends": [
        "stock",
        "sale_stock",
        "sale_management",
        "purchase",
    ],
    "data": [
        "security/picking_security.xml",
        "views/stock_view.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "license": "OPL-1",
}
