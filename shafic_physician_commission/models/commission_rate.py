# -*- coding: utf-8 -*-
from odoo import fields, models


class PhysicianCommissionRate(models.Model):
    """Commission percentage paid to a physician, applied to the
    post-expense base (revenue minus the allocated expense rate)."""
    _name = 'physician.commission.rate'
    _description = 'Physician Commission Rate'
    _rec_name = 'physician_id'

    physician_id = fields.Many2one(
        'hms.physician', string='Physician', required=True,
        ondelete='cascade')
    commission_percent = fields.Float(
        string='Commission %',
        help='Percentage of the post-expense base paid to this physician '
             '(e.g. 25 for Dr Kaahiye, 10 for Dr Ifrah).')
    override_expense = fields.Boolean(
        string='Custom Expense Rate',
        help='Use a different expense rate for this physician instead of '
             'the global default.')
    expense_percent = fields.Float(
        string='Expense %',
        help='Expense rate for this physician, used only when Custom '
             'Expense Rate is ticked.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('physician_uniq', 'unique(physician_id)',
         'There is already a commission rate for this physician.'),
    ]
