# Test Cases — Shafic Pharmacy POS Reporting & Analytics

**Module:** `shafic_pharmacy_reports` · **Version:** 18.0.1.0.0

Acceptance test scenarios for QA. Each case lists preconditions, steps and
the expected result. Execute against a database with the module installed
and at least one branch, POS configuration and a few medicine products.

---

## 1. Installation & Setup

### TC-01 — Module installs cleanly
- **Steps:** Install the module from the Apps menu.
- **Expected:** Installation completes with no error; the
  **Pharmacy POS Reports** menu appears; four `Pharmacy:` scheduled
  actions and four sequences are created.

### TC-02 — Branch creation
- **Steps:** `Configuration → Branches → New`; set name, code, warehouse
  and POS points; save.
- **Expected:** Branch saved; duplicate branch code in the same company
  is rejected.

### TC-03 — Settings persistence
- **Steps:** `Configuration → Settings`; change the expiry alert window
  to 120 days; save; reopen.
- **Expected:** The value 120 is retained.

### TC-04 — Security role visibility
- **Steps:** Log in as a user with only the Pharmacy Cashier role.
- **Expected:** Only the menus permitted to a cashier are visible; the
  Configuration menu is hidden.

---

## 2. Sales Reporting

### TC-05 — Sales report wizard, view
- **Precondition:** At least one closed POS session with sales.
- **Steps:** `Sales Reports → Sales Report`; choose this month; click
  **View Report**.
- **Expected:** The POS Sales list opens, grouped by branch, showing
  net/gross sales and margin.

### TC-06 — Sales report wizard, Excel export
- **Steps:** From the same wizard, click **Export to Excel**.
- **Expected:** An `.xlsx` file downloads with one row per sales line.
  (If `xlsxwriter` is absent, a friendly error is shown instead.)

### TC-07 — Date validation
- **Steps:** In the wizard set Date From later than Date To; click View.
- **Expected:** A validation error prevents the action.

### TC-08 — Product / category / branch / cashier reports
- **Steps:** Open each of Product Sales, Category Sales, Branch
  Performance and Cashier Performance.
- **Expected:** Each opens with list, pivot and graph views and figures
  consistent with the POS data.

---

## 3. Inventory Reporting

### TC-09 — Stock position
- **Steps:** Open `Inventory Reports → Stock Position`.
- **Expected:** Rows show available quantity, batch, expiry and stock
  value per product/warehouse.

### TC-10 — Reorder report
- **Precondition:** A product below its reorder minimum.
- **Steps:** Open `Inventory Reports → Reorder Level Report`.
- **Expected:** The product appears with a positive shortage and a
  suggested order quantity; the *Needs Reorder* filter is applied by
  default.

### TC-11 — Movement analysis refresh
- **Steps:** `Inventory Reports → Inventory Report`; select
  *Stock Movement*; click **Refresh Movement Analysis**.
- **Expected:** The movement report opens; products are classified as
  fast, slow or dead.

---

## 4. Expiry Management

### TC-12 — Expiry buckets
- **Precondition:** Lots with various expiry dates, including expired.
- **Steps:** Open `Expiry Reports → Expiry Dashboard`.
- **Expected:** Rows are bucketed (expired, 30, 60, 90, 180); expired and
  30-day rows are visually highlighted.

### TC-13 — Expiry PDF
- **Steps:** `Expiry Reports → Expiry Report` wizard; choose a window;
  click **Print PDF**.
- **Expected:** A PDF lists the expiring stock with a total value at risk.

### TC-14 — Product recall workflow
- **Precondition:** A product previously sold via POS with lot tracking.
- **Steps:** Create a recall for that product and its lot; click
  **Start Recall**; review affected customers; click
  **Notify Affected Customers**; click **Complete**.
- **Expected:** Affected customers are traced from POS history; emails are
  queued; the recall reaches the Completed state.

---

## 5. Prescription & Compliance

### TC-15 — Prescription lifecycle
- **Steps:** Create a prescription with lines; Validate; Dispense.
- **Expected:** The reference is auto-numbered (`RX/<year>/…`); the state
  bar advances Draft → Validated → Dispensed.

### TC-16 — Prescription PDF
- **Steps:** Print a prescription.
- **Expected:** A PDF shows patient, doctor, branch and prescribed items.

### TC-17 — Controlled drug register auto-entry
- **Precondition:** A product flagged as a controlled drug.
- **Steps:** Sell that product through the POS and close the order.
- **Expected:** A controlled-drug register entry is created automatically
  with the running balance, pharmacist, patient and doctor.

### TC-18 — Insurance claim lifecycle
- **Steps:** Create a claim; Submit; Approve; Mark Paid.
- **Expected:** The reference is auto-numbered (`CLM/<year>/…`); the state
  bar advances correctly; rejected amount is computed.

### TC-19 — Audit trail is read-only
- **Steps:** Open `Compliance Reports → Audit Trail`.
- **Expected:** Entries can be viewed but not created or edited from the UI.

---

## 6. Financial Reporting

### TC-20 — POS session control & Z-report
- **Precondition:** A closed POS session.
- **Steps:** Open `Financial Reports → POS Session Control`; print the
  Z-Report for a session.
- **Expected:** Cash differences are shown; rows with a non-zero
  difference are highlighted; the Z-Report PDF renders.

### TC-21 — Payment & refund analysis
- **Steps:** Open Payment Analysis and Refund Analysis.
- **Expected:** Payment Analysis totals by method reconcile with POS
  payments; Refund Analysis lists refund lines by branch and user.

### TC-22 — Profitability analysis
- **Steps:** Open `Financial Reports → Profitability Analysis`.
- **Expected:** Each line shows margin value, margin % and discount %.

---

## 7. Procurement & Customer

### TC-23 — Supplier performance
- **Precondition:** Confirmed and received purchase orders.
- **Steps:** Open `Procurement Reports → Supplier Performance`.
- **Expected:** Delivery accuracy, on-time rate and average lead time are
  shown per supplier.

### TC-24 — Customer analytics segmentation
- **Steps:** Open `Customer Reports → Customer Analytics`.
- **Expected:** Customers are grouped into segments; spend and visit
  metrics are populated.

---

## 8. Dashboard

### TC-25 — Executive dashboard loads
- **Steps:** Open `Pharmacy POS Reports → Executive Dashboard`.
- **Expected:** KPI tiles render; the seven-day trend and top medicines
  panels populate; values match the underlying reports.

### TC-26 — Branch selector & drill-down
- **Steps:** Change the branch in the selector; click an alert tile.
- **Expected:** KPIs refresh for the chosen branch; the relevant detailed
  report opens on drill-down.

---

## 9. Scheduled Jobs

### TC-27 — Cron jobs run without error
- **Steps:** From Scheduled Actions, manually run each `Pharmacy:` job.
- **Expected:** Each completes without error; the expiry and reorder jobs
  notify the configured users; the refresh job rebuilds movement data.

---

## 10. Multi-Company / Multi-Branch

### TC-28 — Record-rule isolation
- **Precondition:** Two companies with separate branches.
- **Steps:** Log in as a user of company A.
- **Expected:** Only company A branches, prescriptions, claims, recalls
  and audit entries are visible.

### TC-29 — Cashier "own sales" rule
- **Steps:** Log in as a cashier and open the POS Sales report.
- **Expected:** Only that cashier's own sales lines are visible; a manager
  sees all.

---

## Regression Checklist

- [ ] All 42 XML data files load without error.
- [ ] All menus open their target action.
- [ ] All SQL report views are created on install/upgrade.
- [ ] PDF reports render for expiry, Z-report, controlled drug and
      prescription.
- [ ] Excel export produces a valid file.
- [ ] Security: each role sees only its permitted menus and records.
