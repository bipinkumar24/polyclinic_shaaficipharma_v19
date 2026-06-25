# POS Cashier Sales Bonus — Odoo 18

Computes a sales-performance bonus per cashier directly from Point of Sale orders.

## Install
1. Copy the `pos_cashier_bonus` folder into your Odoo 18 addons path.
2. *Apps* → *Update Apps List* → search **POS Cashier Sales Bonus** → Install.
   (Depends on `point_of_sale` and `hr`.)

## Use
*Point of Sale → Cashier Bonus → New*

1. Set the **period** (defaults to the current month).
2. Set **Monthly Target / Cashier** (e.g. 26,250), **Bonus at 100%** (100),
   **Total Allowance Pool** (400) and **Minimum Achievement %** (70).
3. Choose **Identify Cashier By**:
   - *Employee* — uses the cashier on the POS order (multi-employee registers).
   - *Salesperson (User)* — uses the order's responsible user.
4. Press **Compute from POS Sales**. One line per cashier is created with the
   period sales, achievement % and bonus.
5. **Confirm** to lock the run. Print **Cashier Bonus Sheet** for the PDF.

## Bonus rule
```
Achievement %  = Actual POS Sales / Target
Achievement < 70%   -> bonus = 0
Achievement >= 70%  -> bonus = min(Achievement, 100%) x Bonus at 100%
```
- **Cap Bonus at 100%** (on by default) keeps each cashier at the full bonus so
  the payout never exceeds the pool. Turn it off to reward over-achievement.
- **Redistribute Unused Pool** shares the leftover pool equally among cashiers
  who reached 100% of target.

## Order-volume bonus
`Top Order-Volume Bonus` (default $30) is awarded to the cashier with the
**highest number of POS orders** — counted **only among cashiers who reached
the minimum achievement threshold** (default 70%). A cashier below the
threshold cannot win it even with the most orders. The winner is marked with a
star on the sheet. If two or more eligible cashiers tie, the $30 is split
equally between them. It is paid **on top of** the $400 allowance pool, so:

```
Total Payable = Sales Bonus  (drawn from the $400 pool)
              + Volume Bonus (the $30 order-count prize)
```

## Accounting
When a bonus run is **Confirmed**, the module posts a journal entry for the
total payable:

```
Dr  Cashier Bonus Expense Account
Cr  Bonus Payable Account
```

Set the **Bonus Journal**, **Cashier Bonus Expense Account** and **Bonus
Payable Account** in the Accounting section of the form. After the first run
these fields default automatically from the previous run. The posted entry is
dated on the period end and is reachable from the Journal Entry button.

Pressing **Reset to Draft** on a confirmed run reverses the posted entry so the
ledger stays balanced. Paying the bonus (Dr Bonus Payable / Cr Bank) is handled
separately through payroll or a payment.

## Cash-control penalty
On compute, the module measures cash difference **per cashier** and forfeits
part of that cashier's bonus.

For each cashier the closing cash difference of the POS sessions they were
responsible for is taken from the cash gain (overage) and cash loss (shortage)
amounts \u2014 the same figures Odoo posts to the Cash Difference Gain and Cash
Difference Loss accounts. The two are **added together as absolute amounts**
into one total cash difference (the direction, gain or loss, is ignored). The
tiered rule is then read once against that combined figure, as a percentage of
the cashier's own cash sales:

```
total difference <= 1.0% of cash sales  -> no penalty
1.0% < difference <= 1.5%               -> 50% of the bonus forfeited
difference > 1.5%                       -> 100% forfeited
```

The two limits (1.0% and 1.5%) are configurable. Cash difference is attributed
to the cashier responsible for the POS session, so per-cashier figures are
exact when each cashier runs their own session. The journal entry posted on
confirmation reflects the reduced amounts.

## Notes
- Counts only POS orders that have reached the **posted** ledger \u2014 state
  *Posted* (`done`) or *Invoiced*. Orders still in *Draft*, or *Paid* but not
  yet posted (session not closed), are excluded. Refunds (negative orders)
  net the sales down automatically.
- **Sales Basis** switches between tax-included total and untaxed net.
- **POS Registers** optionally restricts the calculation to chosen registers.
- Per-cashier **Target** can be overridden on a line, then recompute.
