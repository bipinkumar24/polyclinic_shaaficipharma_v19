# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class ReportPharmacyStockValuation(models.Model):
    """Inventory valuation by product / category / branch.

    On-hand quantities come from ``stock.quant`` (internal locations) and
    are valued at the product's configured cost (``standard_price``). This
    avoids any dependency on ``stock_account``/``stock_valuation_layer`` so
    the report works whether or not Inventory Valuation is installed.
    """
    _name = 'report.pharmacy.stock.valuation'
    _description = 'Pharmacy Stock Valuation Report'
    _auto = False
    _order = 'stock_value desc'

    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    categ_id = fields.Many2one('product.category', string='Category',
                               readonly=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)
    cost_method = fields.Selection(
        selection=[
            ('standard', 'Standard Price'),
            ('fifo', 'First In First Out (FIFO)'),
            ('average', 'Average Cost (AVCO)'),
        ], string='Costing Method', readonly=True,
        compute='_compute_cost_method')
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)
    quantity = fields.Float(string='Quantity On Hand', readonly=True)
    stock_value = fields.Float(string='Stock Value', readonly=True)
    unit_value = fields.Float(string='Unit Value', readonly=True,
                              aggregator='avg')

    @api.depends('product_id')
    def _compute_cost_method(self):
        """Read the costing method via the ORM.

        ``property_cost_method`` is a company-dependent field on
        ``product.category``; it cannot be read reliably from raw SQL,
        so it is resolved here through the ORM instead.
        """
        for record in self:
            categ = record.product_id.categ_id
            record.cost_method = categ.property_cost_method or False

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(q.id) AS id,
                    q.product_id AS product_id,
                    t.categ_id AS categ_id,
                    t.pharmacy_category_id AS pharmacy_category_id,
                    q.company_id AS company_id,
                    SUM(q.quantity) AS quantity,
                    SUM(q.quantity * COALESCE(
                        (p.standard_price ->> q.company_id::text)::numeric,
                        0.0)) AS stock_value,
                    CASE WHEN SUM(q.quantity) <> 0
                         THEN SUM(q.quantity * COALESCE(
                                  (p.standard_price ->> q.company_id::text)
                                  ::numeric, 0.0))
                              / SUM(q.quantity)
                         ELSE 0.0 END AS unit_value
                FROM stock_quant q
                JOIN stock_location loc ON q.location_id = loc.id
                JOIN product_product p ON q.product_id = p.id
                JOIN product_template t ON p.product_tmpl_id = t.id
                WHERE loc.usage = 'internal'
                GROUP BY q.product_id, t.categ_id, t.pharmacy_category_id,
                         q.company_id
                HAVING SUM(q.quantity) > 0
            )
        """ % self._table)
