# models/pos_customer_activation_reject_wizard.py  (Odoo 18)
from odoo import models, fields, _


class PosCustomerActivationRejectWizard(models.TransientModel):
    _name = 'pos.customer.activation.reject.wizard'
    _description = 'Reject POS Activation – Reason Wizard'

    activation_id = fields.Many2one('pos.customer.activation', required=True)
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        activation = self.activation_id
        if not activation._check_approver_rights(self.env.user):
            raise models.ValidationError(
                _('You need the Accountant role or above to reject.')
            )
        activation._do_reject(self.env.user, self.reason)
        return {'type': 'ir.actions.act_window_close'}
