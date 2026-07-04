# Payment Request Module — Odoo 19

## Overview

A comprehensive payment request management module for Odoo 19 covering all payment types with a structured 4-step approval workflow.

---

## Request Types

| Type | Fields |
|------|--------|
| **Loan** | Purpose, repayment months, auto-computed monthly deduction |
| **Salary Advance** | Month, year, percentage of salary |
| **Overtime** | Work date, hours, hourly rate, auto-computed amount |
| **Purchase Request** | Vendor, PO reference, line items with subtotals |
| **Expense** | Category, period from/to |
| **Other** | Free-form description |

---

## Approval Workflow

```
Requester → [Submit]
     ↓
Dept. Manager → [Review / Reject]
     ↓
Finance Officer → [Verify / Reject]
     ↓
GM Approver → [Final Approve / Reject]
     ↓
APPROVED
```

Each step records:
- Who acted (user)
- When (timestamp)
- Notes/comments
- Email notification sent automatically

---

## Access Groups

| Group | Permissions |
|-------|-------------|
| **Requester** | Create, edit own requests; view own history |
| **Department Manager** | Review submitted requests; view department requests |
| **Finance Officer** | Verify reviewed requests; view all requests |
| **GM / Final Approver** | Final approval of verified requests |
| **Administrator** | Full access, can reset to draft, unlink |

---

## Installation

1. Copy the `payment_request` folder into your Odoo addons directory:
   ```
   /path/to/odoo/addons/payment_request/
   ```

2. Update the apps list in Odoo:
   - Go to **Settings → Apps**
   - Click **Update Apps List**

3. Search for **"Payment Request"** and click **Install**

4. Assign users to the appropriate groups:
   - Go to **Settings → Users**
   - Edit each user and set their **Payment Request** role under the access rights tab

---

## Module Structure

```
payment_request/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── payment_request.py        ← Main model + workflow
│   └── payment_request_line.py   ← Purchase line items
├── wizard/
│   ├── __init__.py
│   ├── payment_request_reject_wizard.py
│   └── payment_request_reject_wizard_view.xml
├── views/
│   ├── payment_request_views.xml  ← Form, list, kanban, search, pivot, graph + actions
│   └── payment_request_menu.xml   ← Menu structure (role-filtered)
├── security/
│   ├── payment_request_security.xml  ← Groups definition
│   └── ir.model.access.csv           ← CRUD permissions per group
├── data/
│   ├── sequence_data.xml          ← PR/YYYY/XXXX sequence
│   └── mail_template_data.xml     ← 5 email templates
├── report/
│   ├── payment_request_report.xml           ← Report action
│   └── payment_request_report_template.xml  ← PDF QWeb template
└── static/src/
    ├── css/payment_request.css
    └── img/icon.png
```

---

## Sequence Format

Requests are auto-numbered as: `PR/2026/0001`, `PR/2026/0002`, etc.

---

## Email Notifications

Automatic emails are sent at each workflow stage:
- **Submitted** → notifies Department Manager
- **Reviewed** → notifies Finance Officer
- **Verified** → notifies GM Approver
- **Approved** → notifies Requester (approval confirmation)
- **Rejected** → notifies Requester (with reason)

---

## PDF Report

The printed report includes:
- Request details and type-specific fields
- Amount requested / approved
- Full approval trail with timestamps
- Signature area (shown on approved requests)

Print via the **Print** button on any non-draft record.

---

## Customisation Notes

- To add new request types: extend `REQUEST_TYPE_SELECTION` in `payment_request.py` and add a new `<page>` tab in `payment_request_views.xml`
- To change the approval chain: modify the `action_review`, `action_verify`, `action_approve` methods and update the `can_*` computed fields
- Multi-company is supported via `company_id`
- Analytic accounting integration available via `analytic_account_id`
