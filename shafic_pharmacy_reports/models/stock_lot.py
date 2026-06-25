# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockLot(models.Model):
    """Lightweight extension of stock.lot with days_to_expiry.

    Odoo 18's stock module already defines an ``expiry_state`` field
    on ``stock.lot`` with its own selection values. We deliberately do
    NOT override it here — replacing the parent selection breaks the
    inherited views and triggers a warning at registry load. The
    days_to_expiry compute below is enough for our own reports;
    everything that previously read lot.expiry_state has been routed
    to ``report.pharmacy.expiry.expiry_bucket`` instead.
    """
    _inherit = 'stock.lot'

    days_to_expiry = fields.Integer(
        string='Days to Expiry', compute='_compute_days_to_expiry',
        store=False)

    @api.depends('expiration_date')
    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for lot in self:
            if not lot.expiration_date:
                lot.days_to_expiry = 0
                continue
            lot.days_to_expiry = (lot.expiration_date.date() - today).days
