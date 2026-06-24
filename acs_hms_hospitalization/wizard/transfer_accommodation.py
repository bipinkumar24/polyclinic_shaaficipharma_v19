# -*- encoding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import ValidationError, UserError


class TransferAccommodation(models.TransientModel):
    _name = "transfer.accommodation"
    _description = "Transfer Accommodation"

    hospitalization_id = fields.Many2one('acs.hospitalization', 'Hospitalization', required=True)
    patient_id = fields.Many2one ('hms.patient','Patient', required=True)
    current_ward = fields.Many2one ('hospital.ward', 'Current Ward/Room')
    current_bed = fields.Many2one ('hospital.bed', 'Current Bed No.')
    new_ward = fields.Many2one ('hospital.ward', 'Ward/Room')
    new_bed = fields.Many2one ('hospital.bed', 'Bed No.')
    acs_transfer_date = fields.Datetime('Transfer Date', default=fields.Datetime.now())

    @api.model
    def default_get(self,fields):
        context = self._context or {}
        res = super(TransferAccommodation, self).default_get(fields)
        hospitalization = self.env['acs.hospitalization'].browse(context.get('active_ids', []))
        res.update({
            'hospitalization_id': hospitalization.id,
            'patient_id': hospitalization.patient_id.id,
            'current_ward': hospitalization.ward_id.id,
            'current_bed': hospitalization.bed_id.id,
        })
        return res

    def acs_transfer_accommodation(self):
        HistoryObj = self.env['patient.accommodation.history']
        hist_id = HistoryObj.search([('hospitalization_id','=',self.hospitalization_id.id), ('bed_id','=',self.current_bed.id),('end_date','=',False)])
        if hist_id.start_date >= self.acs_transfer_date:
            raise ValidationError("The transfer date can't be set before the start date!")
        hist_id.sudo().end_date = self.acs_transfer_date
        self.sudo().current_bed.state = 'free'
        self.sudo().new_bed.state = 'occupied'
        HistoryObj.create({
            'hospitalization_id': self.hospitalization_id.id,
            'patient_id': self.patient_id.id,
            'ward_id': self.new_ward.id,
            'bed_id': self.new_bed.id,
            'start_date': self.acs_transfer_date,
        })
        self.hospitalization_id.write({
            'ward_id': self.new_ward.id,
            'bed_id': self.new_bed.id,
        })
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: