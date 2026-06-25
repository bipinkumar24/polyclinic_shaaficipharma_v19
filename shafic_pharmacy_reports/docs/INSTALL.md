# Installation Guide — Shafic Pharmacy POS Reporting & Analytics

**Module:** `shafic_pharmacy_reports`
**Version:** 18.0.1.0.0
**Target platform:** Odoo 18 (Community or Enterprise)

---

## 1. Prerequisites

### 1.1 Odoo version
This module targets **Odoo 18.0**. It uses Odoo 18 conventions throughout
(`<list>` views, `<chatter/>`, the `point_of_sale._assets_pos` bundle key).
It will not install unmodified on Odoo 17 or earlier.

### 1.2 Required Odoo apps
The following standard apps are declared as dependencies and will be
installed automatically if not already present:

| Technical name | App |
|----------------|-----|
| `base`         | Base |
| `mail`         | Discuss / Messaging |
| `product`      | Products |
| `stock`        | Inventory |
| `sale`         | Sales |
| `purchase`     | Purchase |
| `account`      | Invoicing / Accounting |
| `contacts`     | Contacts |
| `point_of_sale`| Point of Sale |
| `product_expiry`| Expiration Dates (lot/serial expiry) |

### 1.3 Python libraries
| Library | Required for | Install |
|---------|--------------|---------|
| `xlsxwriter` | Excel export from the Sales Report wizard | `pip install xlsxwriter` |

If `xlsxwriter` is not installed, all features still work; only the
**Export to Excel** button raises a friendly error until the library is added.

---

## 2. Installation Steps

### 2.1 Deploy the module files

1. Copy the `shafic_pharmacy_reports` folder into one of your Odoo
   addons paths, for example:

   ```
   /opt/odoo/custom-addons/shafic_pharmacy_reports
   ```

2. Confirm the folder is on the `addons_path` in your Odoo configuration
   file (`odoo.conf`):

   ```ini
   addons_path = /opt/odoo/addons,/opt/odoo/custom-addons
   ```

### 2.2 Update the apps list

1. Restart the Odoo service so the new path is scanned:

   ```bash
   sudo systemctl restart odoo
   ```

2. Log in as an administrator.
3. Enable **Developer Mode** (Settings → Developer Tools → Activate the
   developer mode).
4. Open **Apps**, click **Update Apps List**, and confirm.

### 2.3 Install the module

1. In **Apps**, remove the default *Apps* filter and search for
   **Shafic Pharmacy POS Reporting & Analytics**.
2. Click **Install**. Odoo will pull in any missing dependencies and then
   install this module.

Installation creates the SQL report views, scheduled actions, sequences,
security groups, the mail template and all menus.

---

## 3. Post-Installation Configuration

1. **Branches** — `Pharmacy POS Reports → Configuration → Branches`.
   Create one branch per location and link its warehouse and POS points.
2. **Settings** — `Pharmacy POS Reports → Configuration → Settings`.
   Set the expiry alert window, dead-stock / slow-stock thresholds, the
   near-expiry discount rate, and the expiry-notification users.
3. **Security groups** — `Settings → Users & Companies → Users`.
   Assign each user one of the six pharmacy roles (Cashier, Pharmacist,
   Inventory Officer, Branch Manager, Finance Team, Pharmacy Admin).
4. **Product setup** — on each medicine, open the **Pharmacy** tab and set
   the pharmacy category, controlled-drug flag, prescription requirement,
   drug schedule, storage condition and reorder min/max.

---

## 4. Verifying the Installation

After installation, confirm the following:

- The **Pharmacy POS Reports** top-level menu is visible.
- `Configuration → Branches` opens without error.
- The **Executive Dashboard** loads (it will show zero values until POS
  data exists).
- Under **Settings → Technical → Automation → Scheduled Actions**, four
  jobs prefixed `Pharmacy:` are present and active.
- Under **Settings → Technical → Sequences**, four sequences with codes
  `pharmacy.prescription`, `pharmacy.controlled.drug.log`,
  `pharmacy.insurance.claim` and `pharmacy.product.recall` are present.

---

## 5. Upgrading

To deploy a new version of the module:

1. Replace the `shafic_pharmacy_reports` folder with the new files.
2. Restart the Odoo service.
3. Open **Apps**, locate the module, and click **Upgrade**.

Because all SQL report views are recreated with `CREATE OR REPLACE VIEW`
on every upgrade, schema changes to reporting models are applied cleanly.

---

## 6. Uninstalling

Uninstalling the module from **Apps** removes all module tables, SQL
views, menus, scheduled actions, sequences and security groups.

> **Note:** Operational records created through the module (prescriptions,
> controlled-drug register entries, insurance claims, recalls and audit
> log entries) are deleted on uninstall. Export any data you need to keep
> beforehand.

---

## 7. Troubleshooting

| Symptom | Resolution |
|---------|------------|
| Module not listed in Apps | Confirm the addons path and run **Update Apps List** in developer mode. |
| Dependency error on install | Ensure the host has internet access or the dependency apps are already available in your addons paths. |
| Excel export error | Install `xlsxwriter` on the Odoo server and restart the service. |
| Dashboard empty | Normal until POS sessions are closed; verify branches and POS points are linked. |
| Reports show no rows | SQL-view reports only reflect **paid / done / invoiced** POS orders. |
