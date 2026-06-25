{
    'name': 'Debt Collector Incentive Bonus',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Speed-weighted recovery bonus for debt collectors, with a '
               'per-collector aged-debt eligibility gate.',
    'description': """
Debt Collector Incentive Bonus
==============================
Computes an incentive bonus for debt collectors from the customer payments
they recorded over a chosen period.

Scheme
------
* Attribution: each recovery is credited to the user who recorded the
  customer payment.
* Eligibility gate (per collector): no bonus unless the collector recovers
  more than the gate %% (default 75%%) of the debt aged over the threshold
  (default 30 days) in their opening book. The gate is measured strictly on
  invoice age.
* Two-band payout: between the gate %% and the upper band %% (default 90%%)
  the pool is earned proportionally; above the upper band a kicker is added.
* Speed weighting: every reconciled recovery earns points equal to amount x
  a day-band speed factor, so faster collection is worth more.
* Self-funding pool: a configurable percentage of net reconciled recovery.
* Guardrails: clawback of reversed payments, a manual conduct-penalty per
  collector, and a hardship list of partners excluded from the scheme.

All scheme parameters are configurable on each bonus run.
""",
    'author': 'Salaam Group',
    'license': 'LGPL-3',
    'depends': ['account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/debt_collector_bonus_views.xml',
        'report/bonus_report.xml',
    ],
    'installable': True,
    'application': False,
}
