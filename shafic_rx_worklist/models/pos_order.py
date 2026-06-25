# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosOrder(models.Model):
    """Link a POS order back to the clinic prescription it was started
    from, and mark that prescription dispensed once the order is paid.

    The order is created server-side at payment, so marking dispensed in
    create() fires exactly once, when the sale is real."""
    _inherit = 'pos.order'

    # Set by the POS frontend (plain id) when the order was started from a
    # scanned prescription. An integer round-trips reliably without the
    # clinic model needing to be loaded into the POS.
    rx_prescription_ref = fields.Integer(
        string='Prescription Ref', copy=False)
    rx_prescription_id = fields.Many2one(
        'prescription.order', string='Source Prescription', copy=False,
        index=True, help='The clinic prescription this sale dispensed.')

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        # IMPORTANT: pos.order returns an EMPTY list here by default, which is
        # the sentinel for "load ALL fields" (read([]) reads everything and
        # the POS builds relations for every field). If we append to an empty
        # list we flip it to "load ONLY this field", which silently drops the
        # order's own relations - payment_ids and lines become undefined and
        # the whole POS order summary / customer display crashes.
        #
        # When the list is empty our custom fields are already loaded by the
        # all-fields read, so only append when another module has explicitly
        # restricted the field list (non-empty).
        if result and 'rx_prescription_ref' not in result:
            result.append('rx_prescription_ref')
        return result

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.rx_prescription_ref and not order.rx_prescription_id:
                rx = self.env['prescription.order'].sudo().browse(
                    order.rx_prescription_ref)
                if rx.exists():
                    order.rx_prescription_id = rx.id
            rx = order.rx_prescription_id
            if rx and not rx.acs_rx_dispensed:
                rx.sudo().action_mark_dispensed()
        return orders
