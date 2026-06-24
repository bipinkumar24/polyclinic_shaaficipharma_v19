#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json


class HmsPatient(models.Model):
    _inherit = 'hms.patient'

    def _acs_get_teeth_data(self):
        data = {}
        procedures = self.patient_procedure_ids.filtered(lambda t: t.tooth_ids and t.state=='done')
        for procedure in procedures:
            tooth_is_removed = True if procedure.product_id.dental_procedure_type=='tooth_removal' else False
            for tooth_id in procedure.tooth_ids:
                if procedure.tooth_id not in data:
                    data[tooth_id.id] = {
                        'procedure_details': '<li>%s [%s]</li>' % (procedure.product_id.name, procedure.name),
                        'tooth_is_removed': tooth_is_removed,
                        'show_procedure_image': procedure.product_id.id if procedure.product_id.show_image_in_chart else False
                    }
                else:
                    data[tooth_id.id]['procedure_details'] += '<li>%s [%s]</li>' % (procedure.product_id.name, procedure.name)
                    if tooth_is_removed:
                        data[tooth_id.id]['tooth_is_removed'] = True
                    if procedure.product_id.show_image_in_chart:
                        data[tooth_id.id]['show_procedure_image'] = procedure.product_id.id

        for m_data in data:
            data[m_data]['procedure_details'] = '<b>Performed Procedures</b>&#13;<ul>' + data[m_data]['procedure_details'] + '</ul>'

        self.acs_teeth_json_data = json.dumps(data)

    acs_teeth_json_data = fields.Text(string="Teeth Data", compute="_acs_get_teeth_data")

    def acs_hms_dental_chart(self, param=''):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/acs/dental/%s%s' % (self.id, param),
        }


class HmsTreatment(models.Model):
    _inherit = 'hms.treatment'

    def acs_hms_dental_chart(self):
        self.ensure_one()
        param = '?treatment_id=%s' % (self.id)
        return self.patient_id.acs_hms_dental_chart(param=param)


class HmsPatientProcedure(models.Model):
    _inherit = 'acs.patient.procedure'

    def acs_hms_dental_chart(self):
        self.ensure_one()
        return self.patient_id.acs_hms_dental_chart()


class HmsAppointment(models.Model):
    _inherit = 'hms.appointment'

    def acs_hms_dental_chart(self):
        self.ensure_one()
        param = '?appointment_id=%s' % (self.id)
        return self.patient_id.acs_hms_dental_chart(param=param)


class ACSProduct(models.Model):
    _inherit = 'product.template'

    dental_procedure_type = fields.Selection([('tooth_removal','Remove Tooth'),('Other','Other')])
    show_image_in_chart = fields.Boolean('Show Product Image in Chart', help="Image to show in chart instead of tooth when perfomed this procedure.")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: