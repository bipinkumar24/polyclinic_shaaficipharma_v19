{
    "name": "Import Inventory Adjustment (Odoo 19)",
    "version": "19.0.1.0.0",
    "category": "Inventory",
    'author': 'Do Incredible',
    'license': 'OPL-1',
    "summary": "Import Inventory Adjustment from Excel",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/import_inventory_adjustment_wizard_view.xml",
        "views/menu.xml"
    ],
    "installable": True
}