# -*- coding: utf-8 -*-
{
    "name": "Remote Product Synchronization",
    "summary": "Sync Product Templates from a remote Odoo server via XML-RPC",
    "description": """
Connect to a remote Odoo server, read Product Template (product.template)
records and create/update the corresponding products on this server.

Features:
    * Define one or more remote Odoo servers (URL, database, credentials).
    * Test the connection before syncing.
    * Manual, on-demand synchronization from the server form.
    * Duplicate-safe: products are matched by remote id mapping and by
      Internal Reference (default_code) so re-running the sync updates
      existing records instead of creating duplicates.
    * Ready for scheduled synchronization (a disabled cron is provided).
    """,
    "author": "Bipin Prajapati",
    "category": "Inventory/Inventory",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["product", "stock", "branch", "acs_laboratory", "acs_radiology"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/product_remote_server_views.xml",
        "views/product_template_views.xml",
        "views/patient_laboratory_test_views.xml",
    ],
    "installable": True,
    "application": True,
}
