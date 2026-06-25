# Debt Collector Incentive Bonus (Odoo 18)

Computes a speed-weighted recovery bonus for debt collectors from the
customer payments they recorded over a period.

## How it works

1. **Attribution** — each recovery is credited to the user who recorded the
   customer payment (`create_uid` on `account.payment`).
2. **Opening aged book** — at period start, every receivable aged over the
   threshold (default 30 days) is attributed to a *collector of record* — the
   user who most recently recorded a payment for that customer. The residual
   as of period start is reconstructed from the current residual plus every
   reconciliation made on or after the period start.
3. **Eligibility gate** — a collector earns nothing unless their aged-debt
   recovery exceeds the gate percentage (default 75%) of their opening aged
   book. Measured strictly on invoice age.
4. **Two-band payout** — between the gate % and the upper band % (default 90%)
   the pool is earned proportionally; at or above the upper band a kicker is
   added.
5. **Speed points** — every reconciled recovery earns points equal to amount
   x a day-band speed factor (faster collection scores higher). The pool is
   split among eligible collectors by point share.
6. **Pool** — a configurable percentage (default 2.5%) of total net
   reconciled recovery.
7. **Guardrails** — clawback excludes reversed payments; a manual conduct
   penalty per collector forfeits part of the bonus; hardship partners are
   left out of the scheme entirely.

On confirm, one journal entry is posted: debit Bonus Expense, credit Bonus
Payable. Reset reverses it.

## Configurable parameters

Aged threshold, gate %, upper band %, pool %, kicker type and value, the five
speed factors, the clawback toggle and the hardship partner list — all set on
each bonus run.

## Sharia basis

Structured as Juʿālah (a reward for a defined outcome). The bonus is an
internal HR cost and is never charged to debtors; no late-payment interest
funds the pool.

## Notes / assumptions

- Collector attribution relies on payments being recorded by each collector
  under their own user.
- The opening-book reconstruction ignores credit notes or write-offs posted
  during the period; approve write-offs outside the scheme.
- Amounts use company currency via the partial-reconciliation amounts.

## Access

Menu: **Accounting > Collector Bonus > Debt Collector Bonus**. Read for
Accounting users; create/compute/confirm for Accounting managers.
