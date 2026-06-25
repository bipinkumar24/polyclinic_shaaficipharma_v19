# Shafic Pharmacy POS Reporting & Analytics

A comprehensive retail-pharmacy reporting, analytics and compliance module
for **Odoo 18**, supporting single and multi-branch operations.

---

## Overview

This module extends Odoo Point of Sale, Inventory, Purchase, Accounting
and CRM with pharmacy-specific operational, financial, compliance and
analytical reporting.

## Features

### Sales reporting
Daily / weekly / monthly POS sales analysis by product, category, branch
and cashier, with an on-demand wizard and Excel export.

### Inventory & stock
Stock position, valuation, fast / slow / dead stock classification,
reorder-level planning and batch/lot tracking.

### Expiry management
Expiry alert dashboard, expired and near-expiry tracking bucketed by
window, plus a full product-recall workflow with customer tracing and
email notification.

### Prescription & compliance
Prescription register and PDF, an auto-maintained controlled-drug
register, insurance-claim management and billing analysis, and a
read-only audit trail of sensitive actions.

### Profitability analytics
Line-level margin and discount-impact analysis by product, category and
branch.

### Procurement & supplier
Supplier performance KPIs (delivery accuracy, on-time rate, lead time)
and a purchase-versus-sales comparison.

### Customer & loyalty
Customer segmentation, visit frequency and spend analysis, plus loyalty
points reporting.

### Financial & POS control
POS session Z-reports, cash reconciliation and payment-method analysis.

### Executive dashboard
A real-time OWL dashboard of headline KPIs with branch selection and
drill-down into detailed reports.

### Inventory bonus scorecard
A monthly scorecard that scores the inventory team against three
configurable KPIs — expiry write-off rate (expired value ÷ average stock
value), near-expiry stock caught before loss, and product data
completeness (barcode, internal reference, lot/batch) — and computes the
team bonus pool earned. Targets, baselines and pool weights are set under
Configuration → Settings and are designed to step down each quarter.

---

## Requirements

- Odoo **18.0** (Community or Enterprise)
- Standard apps: `point_of_sale`, `stock`, `purchase`, `account`,
  `sale`, `contacts`, `product_expiry` (installed automatically)
- Optional: `xlsxwriter` Python library for Excel export

## Installation

See [`docs/INSTALL.md`](docs/INSTALL.md) for full instructions.

In short: copy the folder to your addons path, update the apps list in
developer mode, and install **Shafic Pharmacy POS Reporting & Analytics**.

## Documentation

| Document | Audience |
|----------|----------|
| `docs/INSTALL.md` | Administrators — installation & upgrade |
| `docs/TECHNICAL.md` | Developers — architecture & extension points |
| `docs/Shafic_Pharmacy_Reports_User_Manual.docx` | End users — full usage manual |
| `docs/TEST_CASES.md` | QA — acceptance test scenarios |

## Security roles

Six escalating roles: Pharmacy Cashier, Pharmacist, Inventory Officer,
Branch Manager, Finance Team and Pharmacy Admin.

## License

LGPL-3

## Author

Shafic Retail — https://www.shaficretail.com
