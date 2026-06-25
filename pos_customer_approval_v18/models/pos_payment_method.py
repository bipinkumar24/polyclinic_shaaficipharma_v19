# models/pos_payment_method.py  (Odoo 18)
from odoo import models, fields, api


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    check_credit_limit = fields.Boolean(
        string='Check Customer Credit Limit',
        default=False
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        if 'check_credit_limit' not in fields_list:
            fields_list.append('check_credit_limit')
        return fields_list
