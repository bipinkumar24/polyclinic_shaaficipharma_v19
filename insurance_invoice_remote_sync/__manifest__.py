# -*- coding: utf-8 -*-
{
    "name": "Insurance Invoice Remote Synchronization",
    "summary": "One-click migration of insurance invoices from a remote Odoo server",
    "description": """
Extends hms_remote_sync/product_remote_sync's remote-sync engine to migrate
Insurance Invoices (account.move records billed to an insurance company, with
patient_invoice_amount > 0) from a remote Odoo server, together with their
invoice lines and linked commission records (acs.commission).

Scope: ONLY account.move records matching
    [('move_type', '=', 'out_invoice'), ('patient_invoice_amount', '>', 0)]
Vendor bills, credit notes, plain customer invoices and journal entries are
never touched.

Features:
    * Every field resolved against already-synced/existing local records
      (partner, patient, physician, branch, journal, team, salesperson) -
      never fabricates a record for these; skips and logs if unresolved.
    * Historic invoice numbers preserved exactly.
    * Invoices are created in draft and posted via the standard action_post()
      flow - never force-written to 'posted'.
    * Idempotent: matched by remote id, safe to re-run.
    * Manual, one-click sync from the remote server form, plus a
      field-by-field validation report against the full migrated set.
    """,
    "author": "Bipin Prajapati",
    "category": "Accounting",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["hms_remote_sync", "acs_commission", "acs_hms_cashier"],
    "data": [
        "views/product_remote_server_views.xml",
    ],
    "installable": True,
    "application": False,
}
