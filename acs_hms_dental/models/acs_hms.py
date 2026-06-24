#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ACSAppointment(models.Model):
    _inherit = 'hms.appointment'

    medical_questionnaire_ids = fields.One2many('acs.medical.questionnaire', 'appointment_id', 
        string='Medical Questionnaire')
    dental_questionnaire_ids = fields.One2many('acs.dental.questionnaire', 'appointment_id', 
        string='Dental Questionnaire')

    @api.onchange('department_id')
    def onchange_dental_department(self):
        medical_questionnaire_ids = []
        dental_questionnaire_ids = []
        if self.department_id and self.department_id.department_type=='dental':
            questions = self.env['acs.dental.questionnaire.template'].search([])
            for question in questions:
                if question.question_type=='medical':
                    medical_questionnaire_ids.append((0,0,{
                        'name': question.name,
                        'remark': question.remark,
                    }))
                else:
                    dental_questionnaire_ids.append((0,0,{
                        'name': question.name,
                        'remark': question.remark,
                    }))

            self.medical_questionnaire_ids = medical_questionnaire_ids
            self.dental_questionnaire_ids = dental_questionnaire_ids


class AcsPatientProcedure(models.Model):
    _inherit="acs.patient.procedure"

    tooth_surface_ids = fields.Many2many('acs.tooth.surface', string='Surface')
    tooth_ids = fields.Many2many('acs.hms.tooth', string='Tooths')
    #ACS Note: For migration only.
    tooth_id = fields.Many2one('acs.hms.tooth', string='Tooth')


class HrDepartment(models.Model): 
    _inherit = "hr.department"

    department_type = fields.Selection(selection_add=[('dental','Odontology')])


class ACSProduct(models.Model):
    _inherit = 'product.template'

    hospital_product_type = fields.Selection(selection_add=[('dental_procedure','Dental Process')])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: