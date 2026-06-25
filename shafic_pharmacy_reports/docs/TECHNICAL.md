# Technical Documentation — Shafic Pharmacy POS Reporting & Analytics

**Module:** `shafic_pharmacy_reports` · **Version:** 18.0.1.0.0 · **Odoo:** 18.0

This document describes the internal architecture of the module for
developers and technical administrators.

---

## 1. Architecture Overview

The module is a **reporting and compliance layer** on top of standard
Odoo POS, Inventory, Purchase, Accounting and CRM. It contributes:

- **Configuration / master-data models** — branches, pharmacy product
  attributes, patient/doctor/insurer partner attributes, module settings.
- **Operational record models** — prescriptions, controlled-drug register,
  insurance claims, product recalls, audit log.
- **Core-model extensions** — `pos.order`, `pos.order.line`, `pos.session`,
  `stock.lot`, `product.template`, `res.partner`, `res.config.settings`.
- **Reporting models** — SQL-view-backed analytic models (`_auto = False`)
  plus one stored, cron-refreshed model for movement classification.
- **Presentation layer** — backend list/pivot/graph views, three report
  wizards, an OWL executive dashboard, and four QWeb PDF reports.

---

## 2. Module Layout

```
shafic_pharmacy_reports/
├── __manifest__.py
├── __init__.py
├── controllers/          # JSON endpoints for the dashboard
├── data/                 # sequences, cron, mail template, paper formats
├── models/               # all Python models
├── reports/              # QWeb PDF report actions + templates
├── security/             # groups, record rules, access CSV
├── static/src/           # OWL dashboard (js/xml/css) + POS patch
├── views/                # backend views and menu tree
├── wizards/              # report wizards + their views
└── docs/                 # this documentation
```

---

## 3. Data Model

### 3.1 Configuration / master data

| Model | Purpose |
|-------|---------|
| `pharmacy.branch` | Branch master: warehouse, POS points, manager, pharmacists, sales target. |
| `res.config.settings` (extended) | Expiry / dead-stock / slow-stock thresholds, near-expiry discount, notification users. |
| `product.template` / `product.product` (extended) | Pharmacy category, controlled-drug flag, prescription requirement, drug schedule, storage condition, reorder min/max. |
| `res.partner` (extended) | Patient, doctor and insurer flags; computed customer segment and spend/visit metrics. |

### 3.2 Operational records

| Model | Sequence code | Notes |
|-------|---------------|-------|
| `pharmacy.prescription` (+ `.line`) | `pharmacy.prescription` | Draft → Validated → Dispensed → Cancelled. |
| `pharmacy.controlled.drug.log` | `pharmacy.controlled.drug.log` | Auto-created when controlled drugs are sold via POS. |
| `pharmacy.insurance.claim` | `pharmacy.insurance.claim` | Draft → Submitted → Approved/Partial/Rejected → Paid. |
| `pharmacy.product.recall` | `pharmacy.product.recall` | Traces affected customers from POS lot history. |
| `pharmacy.audit.log` | — | Append-only sensitive-action trail. |

### 3.3 Core-model extensions

- `pos.order` — adds `prescription_id`, computed `branch_id`,
  `pharmacist_id`; overrides `_process_order` to create controlled-drug
  register entries.
- `pos.session` — adds computed `branch_id` and `cash_difference`.
- `stock.lot` — adds computed `days_to_expiry` and `expiry_state`.

### 3.4 Reporting models

All analytic reporting models except one are **SQL views**:

- `_auto = False`
- An `init()` method calls `tools.drop_view_if_exists` then issues a
  `CREATE OR REPLACE VIEW` statement.
- They are therefore read-only and rebuilt on every module upgrade.

The single exception is **`report.pharmacy.stock.movement`**, a stored
model whose rows are recomputed by `refresh_movement_analysis()` because
fast/slow/dead classification needs procedural logic and a time window.

| Model | Backing |
|-------|---------|
| `report.pharmacy.sales` | SQL view over `pos.order.line` |
| `report.pharmacy.product.sales` | SQL view, per-product aggregation |
| `report.pharmacy.category.sales` | SQL view by pharmacy category |
| `report.pharmacy.branch.performance` | SQL view per branch |
| `report.pharmacy.cashier.performance` | SQL view per cashier |
| `report.pharmacy.stock.position` | SQL view over `stock.quant` |
| `report.pharmacy.stock.valuation` | SQL view over valuation layers |
| `report.pharmacy.stock.movement` | **Stored**, cron-refreshed |
| `report.pharmacy.batch.tracking` | SQL view over `stock.lot` |
| `report.pharmacy.reorder` | SQL view, available vs reorder min/max |
| `report.pharmacy.expiry` | SQL view, bucketed by days-to-expiry |
| `report.pharmacy.prescription.sales` | SQL view |
| `report.pharmacy.controlled.drug` | SQL view |
| `report.pharmacy.insurance` | SQL view |
| `report.pharmacy.profitability` | SQL view |
| `report.pharmacy.supplier.performance` | SQL view |
| `report.pharmacy.purchase.sales` | SQL view (purchase vs sales) |
| `report.pharmacy.customer` | SQL view |
| `report.pharmacy.loyalty` | SQL view (guarded — checks `loyalty_card` table) |
| `report.pharmacy.pos.control` | SQL view (Z-report data) |
| `report.pharmacy.payment` | SQL view |
| `report.pharmacy.refund` | SQL view |

`pharmacy.dashboard` is an `AbstractModel` exposing
`get_dashboard_data(branch_id)` and `get_branches()`.
`pharmacy.cron` is an `AbstractModel` that hosts all scheduled-job logic.

---

## 4. Security Model

Six `res.groups` form an escalating hierarchy via `implied_ids`:

```
Pharmacy Cashier
   └─ Pharmacist
        └─ Inventory Officer
             └─ Branch Manager
                  └─ Finance Team
                       └─ Pharmacy Admin
```

- `security/pharmacy_security.xml` — module category and the six groups.
- `security/ir.model.access.csv` — model-level ACLs (84 rules); reporting
  models are read-only, wizards are transient with full CRUD for report
  users, the audit log is append-only.
- `security/ir_rule.xml` — multi-company record rules and a cashier
  "see own sales only" rule versus manager "see all" on the sales report.

---

## 5. Scheduled Jobs

Defined in `data/ir_cron_data.xml`, all hosted on `pharmacy.cron`:

| XML id | Method | Frequency |
|--------|--------|-----------|
| `cron_pharmacy_expiry_check` | `cron_expiry_check()` | Daily |
| `cron_pharmacy_reorder_alert` | `cron_reorder_alert()` | Daily |
| `cron_pharmacy_refresh_analysis` | `cron_refresh_analysis()` | Every 6 h |
| `cron_pharmacy_insurance_sync` | `cron_insurance_sync()` | Daily |

`cron_refresh_analysis()` delegates to
`report.pharmacy.stock.movement.refresh_movement_analysis()`.

---

## 6. Frontend

### 6.1 Executive dashboard (OWL)

- `static/src/js/dashboard.js` — `PharmacyDashboard` OWL component,
  registered in the `actions` registry under the tag
  `shafic_pharmacy_dashboard`. Data is fetched through `useService("orm")`
  by calling the `pharmacy.dashboard` abstract model.
- `static/src/xml/dashboard.xml` — the component template
  (`shafic_pharmacy_reports.PharmacyDashboard`).
- `static/src/css/dashboard.css` — dashboard styling.
- Registered in the `web.assets_backend` bundle.

`controllers/dashboard_controller.py` additionally exposes
`/shafic_pharmacy/dashboard_data` and `/shafic_pharmacy/branches` as
`type='json'` endpoints for any external/JSON-RPC consumer.

### 6.2 POS extension

`static/src/js/pos_prescription.js` patches the POS `PosOrder` prototype
to carry `prescription_id` / `pharmacist_id` and to export them for the
receipt. Registered in the `point_of_sale._assets_pos` bundle.

---

## 7. PDF Reports

Defined in `reports/report_actions.xml` with templates in the same folder:

| Report action | Model | Template |
|----------------|-------|----------|
| `action_report_pharmacy_expiry` | `report.pharmacy.expiry` | `report_expiry_document` |
| `action_report_pharmacy_z_report` | `report.pharmacy.pos.control` | `report_z_report_document` |
| `action_report_pharmacy_controlled_drug` | `pharmacy.controlled.drug.log` | `report_controlled_drug_document` |
| `action_report_pharmacy_prescription` | `pharmacy.prescription` | `report_prescription_document` |

The expiry PDF action id `action_report_pharmacy_expiry` is referenced by
the Expiry Report wizard's `action_print_pdf` method.

---

## 8. Extension Points

- **New report** — add a SQL-view model under `models/`, register it in
  `models/__init__.py`, add a view file and action, add the file to the
  manifest `data` list, add an ACL row, and add a menu entry.
- **New dashboard KPI** — extend `pharmacy.dashboard.get_dashboard_data()`
  and add the corresponding markup in `dashboard.xml`.
- **New scheduled job** — add a method to `pharmacy.cron` and a record to
  `data/ir_cron_data.xml`.

---

## 9. Conventions

- Odoo 18 view syntax (`<list>`, `<chatter/>`).
- SQL-view models use `_auto = False` + `init()` with
  `tools.drop_view_if_exists` + `CREATE OR REPLACE VIEW`.
- POS order states considered "sales": `paid`, `done`, `invoiced`.
- `pos.order.line` cost field used: `total_cost`.
- All monetary computed fields are `readonly` on reporting models.
