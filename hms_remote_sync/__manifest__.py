# -*- coding: utf-8 -*-
{
    "name": "HMS Remote Master Data Synchronization",
    "summary": "Sync HMS patient/physician/department master data from a remote Odoo server",
    "description": """
Extends product_remote_sync's generic remote-sync engine (product.remote.server)
to migrate hms.patient master data from a remote Odoo server, reusing the
already-synced res.partner/product.template records rather than duplicating
them.

Features:
    * Departments (hr.department), Physicians (hms.physician) and Patients
      (hms.patient) are synced in dependency order, each matched by remote id
      so re-running the sync updates existing records instead of duplicating.
    * A patient's Related Partner (and Insurance Company) always link to an
      already-synced local res.partner — never fabricated or name-matched.
    * Migrated physicians default to Portal-only access (no backend login)
      until manually promoted, one doctor at a time.
    * Manual, on-demand synchronization from the remote server form, with a
      test-batch (dry run) action bounded by the existing Test Batch Size.
    """,
    "author": "Bipin Prajapati",
    "category": "Medical",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["product_remote_sync", "acs_hms"],
    "data": [
        "views/product_remote_server_views.xml",
    ],
    "installable": True,
    "application": False,
}
