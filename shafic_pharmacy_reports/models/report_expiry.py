# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportPharmacyExpiry(models.Model):
    """Expiry management report - alert buckets, expired & near-expiry."""
    _name = 'report.pharmacy.expiry'
    _description = 'Pharmacy Expiry Report'
    _auto = False
    _order = 'expiration_date'

    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Batch / Lot',
                             readonly=True)
    lot_name = fields.Char(string='Batch Number', readonly=True)
    expiration_date = fields.Datetime(string='Expiry Date', readonly=True)
    days_to_expiry = fields.Integer(string='Days to Expiry', readonly=True)
    expiry_bucket = fields.Selection(
        selection=[
            ('expired', 'Expired'),
            ('30', 'Within 30 Days'),
            ('60', 'Within 60 Days'),
            ('90', 'Within 90 Days'),
            ('180', 'Within 180 Days'),
            ('ok', 'Beyond 180 Days'),
        ], string='Expiry Bucket', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    stock_value = fields.Float(string='Stock Value', readonly=True)
    margin_lost = fields.Float(
        string='Margin Lost', readonly=True,
        help='Estimated lost margin: list price minus cost, multiplied '
             'by quantity. Shows the real financial impact rather than '
             'just the cost write-off.')
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    q.id AS id,
                    q.product_id AS product_id,
                    t.pharmacy_category_id AS pharmacy_category_id,
                    q.lot_id AS lot_id,
                    sl.name AS lot_name,
                    sl.expiration_date AS expiration_date,
                    (sl.expiration_date::date - CURRENT_DATE)
                        AS days_to_expiry,
                    CASE
                        WHEN sl.expiration_date::date < CURRENT_DATE
                            THEN 'expired'
                        WHEN sl.expiration_date::date
                             <= CURRENT_DATE + INTERVAL '30 days'
                            THEN '30'
                        WHEN sl.expiration_date::date
                             <= CURRENT_DATE + INTERVAL '60 days'
                            THEN '60'
                        WHEN sl.expiration_date::date
                             <= CURRENT_DATE + INTERVAL '90 days'
                            THEN '90'
                        WHEN sl.expiration_date::date
                             <= CURRENT_DATE + INTERVAL '180 days'
                            THEN '180'
                        ELSE 'ok'
                    END AS expiry_bucket,
                    q.quantity AS quantity,
                    q.quantity *
                        COALESCE(
                            (p.standard_price ->> q.company_id::text)::numeric,
                            0.0)
                        AS stock_value,
                    q.quantity *
                        GREATEST(
                            COALESCE(t.list_price, 0.0) -
                            COALESCE(
                                (p.standard_price ->> q.company_id::text)
                                ::numeric, 0.0),
                            0.0)
                        AS margin_lost,
                    q.company_id AS company_id
                FROM stock_quant q
                JOIN stock_location loc ON q.location_id = loc.id
                JOIN stock_lot sl ON q.lot_id = sl.id
                JOIN product_product p ON q.product_id = p.id
                JOIN product_template t ON p.product_tmpl_id = t.id
                WHERE loc.usage = 'internal'
                  AND q.quantity > 0
                  AND sl.expiration_date IS NOT NULL
            )
        """ % self._table)

    def _record_catch_action(self, action_type):
        """Create a pharmacy.expiry.action row for each selected line.

        Returns a notification action so the UI confirms the catch was
        recorded.
        """
        Action = self.env['pharmacy.expiry.action']
        created = 0
        for line in self:
            Action.create({
                'action_date': fields.Date.context_today(self),
                'action_type': action_type,
                'product_id': line.product_id.id,
                'lot_id': line.lot_id.id if line.lot_id else False,
                'quantity': line.quantity,
                'value_at_risk': line.stock_value,
                'expiry_date': (line.expiration_date.date()
                                if line.expiration_date else False),
                'company_id': line.company_id.id,
            })
            created += 1
        labels = {
            'discount': 'Discount applied',
            'supplier_return': 'Supplier return arranged',
            'transfer': 'Transfer requested',
            'clearance': 'Marked for clearance',
            'writeoff': 'Write-off acknowledged',
        }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': labels.get(action_type, 'Catch recorded'),
                'message': '%d catch action(s) recorded. These count '
                           'toward this month\'s caught-early bonus.'
                           % created,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_record_discount(self):
        return self._record_catch_action('discount')

    def action_record_supplier_return(self):
        return self._record_catch_action('supplier_return')

    def action_record_transfer(self):
        return self._record_catch_action('transfer')

    def action_record_clearance(self):
        return self._record_catch_action('clearance')
