# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ShaficPhysicianPerformance(models.Model):
    """Read-only analysis view: one row per patient-invoice product line,
    tagged with the invoice's physician and the line's service type.

    Backed by a SQL view so it powers native pivot / graph / list analytics
    (revenue per physician, by service, volumes, paid vs outstanding, ranking)
    with no stored duplication.
    """
    _name = "shafic.physician.performance"
    _description = "Physician Performance (Analysis)"
    _auto = False
    _order = "invoice_date desc"

    move_id = fields.Many2one("account.move", string="Invoice", readonly=True)
    physician_id = fields.Many2one("hms.physician", string="Physician", readonly=True)
    patient_id = fields.Many2one("res.partner", string="Patient", readonly=True)
    product_id = fields.Many2one("product.product", string="Service / Product", readonly=True)
    categ_id = fields.Many2one("product.category", string="Product Category", readonly=True)
    service_type = fields.Char(string="Service Type", readonly=True)
    invoice_date = fields.Date(string="Date", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    payment_state = fields.Selection(
        selection=[
            ("not_paid", "Not Paid"),
            ("in_payment", "In Payment"),
            ("paid", "Paid"),
            ("partial", "Partially Paid"),
            ("reversed", "Reversed"),
            ("invoicing_legacy", "Invoicing App Legacy"),
        ],
        string="Payment Status", readonly=True)
    revenue = fields.Float(string="Revenue", readonly=True)
    quantity = fields.Float(string="Quantity", readonly=True)
    line_count = fields.Integer(string="Lines", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        # Service type is derived from the product's hospital_product_type when
        # that field is present (ACS HMS), else everything is "Other".
        if "hospital_product_type" in self.env["product.template"]._fields:
            service_sql = """
                CASE
                    WHEN pt.hospital_product_type = 'consultation' THEN 'Consultation'
                    WHEN pt.hospital_product_type = 'procedure'    THEN 'Procedure'
                    WHEN pt.hospital_product_type = 'medicament'   THEN 'Pharmacy'
                    WHEN pt.hospital_product_type IS NULL          THEN 'Other'
                    ELSE initcap(replace(pt.hospital_product_type, '_', ' '))
                END
            """
        else:
            service_sql = "'Other'"

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    l.id                AS id,
                    l.move_id           AS move_id,
                    m.physician_id      AS physician_id,
                    m.partner_id        AS patient_id,
                    l.product_id        AS product_id,
                    pt.categ_id         AS categ_id,
                    l.company_id        AS company_id,
                    m.invoice_date      AS invoice_date,
                    m.payment_state     AS payment_state,
                    l.price_subtotal    AS revenue,
                    l.quantity          AS quantity,
                    1                   AS line_count,
                    %s                  AS service_type
                FROM account_move_line l
                JOIN account_move m         ON m.id = l.move_id
                LEFT JOIN product_product pp  ON pp.id = l.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE m.move_type = 'out_invoice'
                  AND m.state = 'posted'
                  AND l.display_type = 'product'
                  AND l.product_id IS NOT NULL
                  AND m.physician_id IS NOT NULL
            )
        """ % (self._table, service_sql))
