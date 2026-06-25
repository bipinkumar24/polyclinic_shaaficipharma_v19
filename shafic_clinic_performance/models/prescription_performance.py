# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ShaficPhysicianPrescription(models.Model):
    """Read-only analysis view: one row per prescription line, tagged with the
    prescribing physician. Powers 'physician by prescription count and value'.

    * Prescription count = sum of ``prescription_count`` (a per-prescription
      flag set on the first line of each prescription), so it counts whole
      prescriptions, not lines.
    * Value = quantity x the medicament's sale price (prescription lines carry
      no price of their own).
    """
    _name = "shafic.physician.prescription"
    _description = "Physician Prescription Analysis"
    _auto = False
    _order = "date desc"

    prescription_id = fields.Many2one("prescription.order", string="Prescription", readonly=True)
    physician_id = fields.Many2one("hms.physician", string="Physician", readonly=True)
    patient_id = fields.Many2one("hms.patient", string="Patient", readonly=True)
    product_id = fields.Many2one("product.product", string="Medicament", readonly=True)
    categ_id = fields.Many2one("product.category", string="Product Category", readonly=True)
    date = fields.Date(string="Date", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    quantity = fields.Float(string="Units", readonly=True)
    value = fields.Float(string="Value", readonly=True)
    prescription_count = fields.Integer(string="Prescriptions", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    l.id                AS id,
                    l.prescription_id   AS prescription_id,
                    p.physician_id      AS physician_id,
                    p.patient_id        AS patient_id,
                    l.product_id        AS product_id,
                    pt.categ_id         AS categ_id,
                    p.prescription_date::date AS date,
                    p.company_id        AS company_id,
                    l.quantity          AS quantity,
                    (l.quantity * COALESCE(pt.list_price, 0.0)) AS value,
                    CASE WHEN l.id = (
                            SELECT MIN(l2.id) FROM prescription_line l2
                            WHERE l2.prescription_id = l.prescription_id
                         ) THEN 1 ELSE 0 END AS prescription_count
                FROM prescription_line l
                JOIN prescription_order p ON p.id = l.prescription_id
                LEFT JOIN product_product pp  ON pp.id = l.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE l.product_id IS NOT NULL
            )
        """ % self._table)
