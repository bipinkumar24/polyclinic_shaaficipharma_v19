# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ShaficScriptCapture(models.Model):
    """Script capture analysis: did a prescribed medicament get dispensed at
    our own pharmacy/clinic?

    There is no hard link from a sale back to the prescription, so capture is
    inferred: a prescription line (patient P, product M, date D) is *captured*
    if there is a sale of product M to P's customer record within a window of
    D days, in POS or on a posted patient invoice. This is a heuristic — see
    the caveats surfaced in the dashboard.
    """
    _name = "shafic.script.capture"
    _description = "Script Capture Analysis"
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
    prescribed_value = fields.Float(string="Prescribed Value", readonly=True)
    captured = fields.Boolean(string="Filled with us", readonly=True)
    captured_value = fields.Float(string="Captured Value", readonly=True)
    captured_count = fields.Integer(string="Captured Lines", readonly=True)
    line_count = fields.Integer(string="Prescribed Lines", readonly=True)
    script_count = fields.Integer(string="Prescriptions", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        win = int(self.env["ir.config_parameter"].sudo().get_param(
            "shafic_clinic.capture_window_days", default="14") or 14)

        has_partner = "partner_id" in self.env["hms.patient"]._fields
        clauses = []
        if has_partner and "pos.order.line" in self.env:
            clauses.append("""
                EXISTS (SELECT 1 FROM pos_order_line sol
                        JOIN pos_order so ON so.id = sol.order_id
                        WHERE sol.product_id = l.product_id
                          AND so.partner_id = l.partner_id
                          AND so.state IN ('paid','done','invoiced')
                          AND so.date_order::date >= l.d0
                          AND so.date_order::date <= l.d0 + %d)""" % win)
        if has_partner:
            clauses.append("""
                EXISTS (SELECT 1 FROM account_move_line aml
                        JOIN account_move am ON am.id = aml.move_id
                        WHERE aml.product_id = l.product_id
                          AND am.partner_id = l.partner_id
                          AND am.move_type = 'out_invoice'
                          AND am.state = 'posted'
                          AND am.invoice_date >= l.d0
                          AND am.invoice_date <= l.d0 + %d)""" % win)
        captured_expr = "(%s)" % " OR ".join(clauses) if clauses else "FALSE"
        partner_sel = "pat.partner_id" if has_partner else "NULL::integer"

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH base AS (
                    SELECT
                        pl.id AS id, pl.prescription_id AS prescription_id,
                        p.physician_id AS physician_id, p.patient_id AS patient_id,
                        pl.product_id AS product_id, pt.categ_id AS categ_id,
                        p.prescription_date::date AS date, p.company_id AS company_id,
                        pl.quantity AS quantity,
                        (pl.quantity * COALESCE(pt.list_price, 0.0)) AS prescribed_value,
                        %s AS partner_id,
                        p.prescription_date::date AS d0
                    FROM prescription_line pl
                    JOIN prescription_order p ON p.id = pl.prescription_id
                    JOIN hms_patient pat ON pat.id = p.patient_id
                    LEFT JOIN product_product pp  ON pp.id = pl.product_id
                    LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE pl.product_id IS NOT NULL
                )
                SELECT
                    l.id, l.prescription_id, l.physician_id, l.patient_id,
                    l.product_id, l.categ_id, l.date, l.company_id, l.quantity,
                    l.prescribed_value,
                    %s AS captured,
                    CASE WHEN %s THEN l.prescribed_value ELSE 0.0 END AS captured_value,
                    CASE WHEN %s THEN 1 ELSE 0 END AS captured_count,
                    1 AS line_count,
                    CASE WHEN l.id = (SELECT MIN(l2.id) FROM prescription_line l2
                                      WHERE l2.prescription_id = l.prescription_id)
                         THEN 1 ELSE 0 END AS script_count
                FROM base l
            )
        """ % (self._table, partner_sel, captured_expr, captured_expr, captured_expr))
