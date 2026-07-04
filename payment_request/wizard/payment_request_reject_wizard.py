from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PaymentRequestRejectWizard(models.TransientModel):
    _name = 'payment.request.reject.wizard'
    _description = 'Reject Payment Request Wizard'

    request_id = fields.Many2one('payment.request', string='Payment Request', required=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        req = self.request_id
        req.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
            'rejected_by': self.env.user.id,
            'date_rejected': fields.Datetime.now(),
        })
        req.message_post(
            body=_('Request rejected by %s.\n\nReason: %s') % (
                self.env.user.name, self.rejection_reason
            )
        )
        req._send_notification_email('rejected')
        return {'type': 'ir.actions.act_window_close'}
