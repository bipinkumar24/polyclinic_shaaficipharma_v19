# coding: utf-8

from odoo import models, api, fields


class AcsCancelReasonWiz(models.TransientModel):
    _name = 'acs.cancel.reason.wiz'
    _description = "Cancellation Reason"

    cancel_reason_id = fields.Many2one('acs.cancel.reason', string='Cancellation Reason', required=True)
    cancel_reason = fields.Text(string="Reason", required=True)

    is_send_mail = fields.Boolean(string="Send Mail")
    template_id = fields.Many2one('mail.template', string="Email Template", default=lambda self: self._default_email_template(),
                                  domain=[('model','=','hms.appointment')])

    @api.onchange('cancel_reason_id')
    def onchange_reason(self):
        if self.cancel_reason_id:
            self.cancel_reason = self.cancel_reason_id.name

    def _default_email_template(self):
        template = self.env.ref('acs_hms.email_template_appointment_cancel', raise_if_not_found=False)
        return template.id if template else False

    def cancel_appointment(self):
        appointment = self.env['hms.appointment'].search([('id','=',self.env.context.get('active_id'))])
        appointment.cancel_reason = self.cancel_reason
        appointment.cancel_reason_id = self.cancel_reason_id.id

        if self.is_send_mail and self.template_id:
            self.template_id.send_mail(appointment.id, force_send=True)
        
        appointment.appointment_cancel()
        return True
