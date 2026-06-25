# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ControlledDrugLog(models.Model):
    _name = 'pharmacy.controlled.drug.log'
    _description = 'Controlled Drug Register Entry'
    _order = 'dispense_date desc, id desc'

    name = fields.Char(
        string='Register Ref.', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    dispense_date = fields.Datetime(
        string='Dispense Date/Time', required=True,
        default=fields.Datetime.now)
    product_id = fields.Many2one(
        'product.product', string='Controlled Drug', required=True,
        domain=[('is_controlled_drug', '=', True)])
    lot_id = fields.Many2one('stock.lot', string='Batch / Lot')
    quantity = fields.Float(string='Dispensed Qty', required=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch')
    pharmacist_id = fields.Many2one(
        'res.users', string='Pharmacist', required=True,
        default=lambda self: self.env.user)
    patient_id = fields.Many2one('res.partner', string='Patient')
    doctor_id = fields.Many2one(
        'res.partner', string='Prescribing Doctor',
        domain=[('is_doctor', '=', True)])
    prescription_id = fields.Many2one(
        'pharmacy.prescription', string='Prescription')
    pos_order_id = fields.Many2one('pos.order', string='POS Order')
    balance_after = fields.Float(
        string='Balance After Dispense',
        help='On-hand quantity recorded after this dispense event.')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    note = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pharmacy.controlled.drug.log') or _('New')
        return super().create(vals_list)
