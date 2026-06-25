# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    prescription_id = fields.Many2one(
        'pharmacy.prescription', string='Prescription',
        help='Prescription linked to this POS order.')
    branch_id = fields.Many2one(
        'pharmacy.branch', string='Branch', compute='_compute_branch_id',
        store=True)
    pharmacist_id = fields.Many2one('res.users', string='Pharmacist')

    @api.depends('config_id')
    def _compute_branch_id(self):
        branch_model = self.env['pharmacy.branch']
        for order in self:
            branch = branch_model.search(
                [('pos_config_ids', 'in', order.config_id.id)], limit=1)
            order.branch_id = branch.id if branch else False

    def _create_controlled_drug_logs(self):
        """Generate controlled drug register entries for controlled
        products contained in the order."""
        log_model = self.env['pharmacy.controlled.drug.log']
        for order in self:
            for line in order.lines:
                if line.product_id.is_controlled_drug and line.qty > 0:
                    log_model.create({
                        'dispense_date': order.date_order,
                        'product_id': line.product_id.id,
                        'quantity': line.qty,
                        'branch_id': order.branch_id.id,
                        'pharmacist_id': (order.pharmacist_id.id or
                                          order.user_id.id),
                        'patient_id': order.partner_id.id,
                        'prescription_id': order.prescription_id.id,
                        'pos_order_id': order.id,
                    })

    @api.model
    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        pos_order = self.browse(order_id)
        if pos_order.exists():
            pos_order._create_controlled_drug_logs()
        return order_id


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category',
        related='product_id.pharmacy_category_id', store=True, readonly=True)
