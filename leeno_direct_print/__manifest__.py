# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Odoo Direct Print",
    "version": "19.0.1.0.0",
    "summary": "Print documents and product labels via the browser print dialog — works with any local or network printer.",
    "description": "",
    "author": "Leeno Consult",
    "website": "https://www.leenconsult.com",
    "category": "Productivity",
    "depends": ["product", "account", "sale", "purchase", "stock", "acs_hms", "acs_radiology", "acs_laboratory"],
    "data": [
        "security/ir.model.access.csv",
        "views/leeno_direct_print_views.xml",
        # "views/label_print_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "leeno_direct_print/static/src/js/browser_print_action.js",
            "leeno_direct_print/static/src/js/label_print_action.js",
        ],
    },
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
