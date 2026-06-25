# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyPrescriptionSales(models.Model):
    """Prescription sales and doctor prescribing analysis."""
    _name = 'report.pharmacy.prescription.sales'
    _description = 'Pharmacy Prescription Sales Report'
    _auto = False
    _order = 'prescription_date desc'

    prescription_id = fields.Many2one(
        'pharmacy.prescription', string='Prescription', readonly=True)
    prescription_no = fields.Char(string='Prescription No.', readonly=True)
    prescription_date = fields.Date(string='Date', readonly=True)
    doctor_id = fields.Many2one('res.partner', string='Doctor',
                                readonly=True)
    patient_id = fields.Many2one('res.partner', string='Patient',
                                 readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    product_id = fields.Many2one('product.product', string='Medicine',
                                 readonly=True)
    is_controlled = fields.Boolean(string='Controlled Drug', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    line_count = fields.Integer(string='Line Count', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    pl.id AS id,
                    p.id AS prescription_id,
                    p.name AS prescription_no,
                    p.prescription_date AS prescription_date,
                    p.doctor_id AS doctor_id,
                    p.patient_id AS patient_id,
                    p.branch_id AS branch_id,
                    pl.product_id AS product_id,
                    t.is_controlled_drug AS is_controlled,
                    pl.quantity AS quantity,
                    1 AS line_count,
                    p.company_id AS company_id
                FROM pharmacy_prescription_line pl
                JOIN pharmacy_prescription p
                    ON pl.prescription_id = p.id
                JOIN product_product pp ON pl.product_id = pp.id
                JOIN product_template t ON pp.product_tmpl_id = t.id
                WHERE p.state != 'cancelled'
            )
        """ % self._table)


class ReportPharmacyControlledDrug(models.Model):
    """Controlled drugs register report view."""
    _name = 'report.pharmacy.controlled.drug'
    _description = 'Pharmacy Controlled Drugs Register Report'
    _auto = False
    _order = 'dispense_date desc'

    log_id = fields.Many2one('pharmacy.controlled.drug.log',
                             string='Register Entry', readonly=True)
    dispense_date = fields.Datetime(string='Dispense Date', readonly=True)
    product_id = fields.Many2one('product.product', string='Drug',
                                 readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Batch', readonly=True)
    quantity = fields.Float(string='Dispensed Qty', readonly=True)
    pharmacist_id = fields.Many2one('res.users', string='Pharmacist',
                                    readonly=True)
    patient_id = fields.Many2one('res.partner', string='Patient',
                                 readonly=True)
    doctor_id = fields.Many2one('res.partner', string='Doctor',
                                readonly=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch',
                                readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    log.id AS id,
                    log.id AS log_id,
                    log.dispense_date AS dispense_date,
                    log.product_id AS product_id,
                    log.lot_id AS lot_id,
                    log.quantity AS quantity,
                    log.pharmacist_id AS pharmacist_id,
                    log.patient_id AS patient_id,
                    log.doctor_id AS doctor_id,
                    log.branch_id AS branch_id,
                    log.company_id AS company_id
                FROM pharmacy_controlled_drug_log log
            )
        """ % self._table)
