from odoo import api, fields, models


class PaymentRequestLine(models.Model):
    _name = 'payment.request.line'
    _description = 'Payment Request Line (Purchase Items)'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        'payment.request',
        string='Payment Request',
        required=True,
        ondelete='cascade',
    )
    description = fields.Char(string='Description / Item', required=True)
    quantity = fields.Float(string='Qty', default=1.0, digits=(12, 2))
    unit_price = fields.Float(string='Unit Price', digits=(12, 2))
    uom = fields.Char(string='Unit', size=20)
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
        digits=(12, 2),
    )
    currency_id = fields.Many2one(
        related='request_id.currency_id',
        string='Currency',
        readonly=True,
    )

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
