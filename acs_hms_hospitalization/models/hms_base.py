# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class AccountMove(models.Model):
    _inherit = "account.move"

    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Hospitalization',
        help="Enter the patient hospitalization code")
    hospital_invoice_type = fields.Selection(selection_add=[('hospitalization', 'Hospitalization')])

    #In lab module it get implemented.
    def acs_get_lab_data(self, invoice_id=False):
        return []
    
    #In radio module it get implemented.
    def acs_get_radiology_data(self, invoice_id=False):
        return []
    
    #In nursing module it get implemented.
    def acs_get_nurse_round_data(self, invoice_id=False):
        return []
    
    def acs_update_invoice_line(self):
        for line in self.invoice_line_ids:
            line.unlink()

        #consumable
        for consumable_line in self.hospitalization_id.consumable_line_ids.filtered(lambda c: c.invoice_id):
            consumable_line.invoice_id = False

        #Physician Rounds
        for physician_ward_round_line in self.hospitalization_id.physician_ward_round_ids.filtered(lambda pwr: pwr.invoice_id):
            physician_ward_round_line.invoice_id = False

        #Procedure
        for procedure in self.hospitalization_id.procedure_ids.filtered(lambda proc: proc.invoice_id):
            procedure.invoice_id = False

        #Surgery
        for surgery in self.hospitalization_id.surgery_ids.filtered(lambda s: s.invoice_id):
            surgery.invoice_id = False

        #Prescription
        for prescription in self.hospitalization_id.prescription_ids.filtered(lambda pre: pre.invoice_id):
            prescription.invoice_id = False
        
        #Nurse Rounds
        self.acs_get_nurse_round_data()

        #Lab
        self.acs_get_lab_data()

        #Radiology
        self.acs_get_radiology_data()

        self.hospitalization_id.acs_hospitalization_invoicing(self)

class Prescription(models.Model):
    _inherit = 'prescription.order'

    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Hospitalization',
        help="Enter the patient hospitalization code")
    ward_id = fields.Many2one('hospital.ward', string='Ward/Room No.', ondelete="restrict")
    bed_id = fields.Many2one("hospital.bed", string="Bed No.", ondelete="restrict")
    ward_round_id = fields.Many2one("ward.rounds", string="Ward Round", ondelete="restrict")
    print_in_discharge = fields.Boolean('Print In Discharge')
 

class ACSAppointment(models.Model):
    _inherit = 'hms.appointment'

    hospitalization_ids = fields.One2many('acs.hospitalization', 'appointment_id',string='Hospitalizations')

    def action_hospitalization(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_hospitalization.acs_action_form_inpatient")
        action['domain'] = [('appointment_id', '=', self.id)]
        action['context'] = {
            'default_patient_id': self.patient_id.id,
            'default_department_id': self.department_id and self.department_id.id or False,
            'default_appointment_id': self.id,
            'default_diseases_ids': [(6,0,self.diseases_ids.ids)],
            'default_physician_id': self.physician_id.id}
        return action


class ACSPatient(models.Model):
    _inherit = "hms.patient"
    
    def _get_hospitalization_count(self):
        for rec in self:
            rec.hospitalization_count = len(rec.hospitalization_ids)

    hospitalization_ids = fields.One2many('acs.hospitalization', 'patient_id',string='Hospitalizations')
    hospitalization_count = fields.Integer(compute='_get_hospitalization_count', string='# Hospitalizations')
    death_register_id = fields.Many2one('patient.death.register', string='Death Register')

    hospitalized = fields.Boolean()
    discharged = fields.Boolean()

    @api.onchange('death_register_id')   
    def onchange_death_register(self):
        if self.death_register_id:
            self.date_of_death = self.death_register_id.date_of_death

    def action_hospitalization(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_hospitalization.acs_action_form_inpatient")
        action['domain'] = [('patient_id', '=', self.id)]
        action['context'] = {'default_patient_id': self.id}
        return action


class StockMove(models.Model):
    _inherit = "stock.move"
    
    hospitalization_id = fields.Many2one('acs.hospitalization', 'Hospitalization')


class ACSConsumableLine(models.Model):
    _inherit = "hms.consumable.line"

    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Hospitalization')


class ACSSurgery(models.Model):
    _inherit = "hms.surgery"

    hospital_ot_id = fields.Many2one('acs.hospital.ot', ondelete="restrict", 
        string='Operation Theater')
    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Hospitalization')


class AcsPrescriptionLine(models.Model):
    _inherit = "prescription.line"
    
    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Inpatient')


class product_template(models.Model):
    _inherit = "product.template"

    hospital_product_type = fields.Selection(selection_add=[('bed', 'Bed')])


class AcsPatientEvaluation(models.Model):
    _inherit = 'acs.patient.evaluation'

    hospitalization_id = fields.Many2one('acs.hospitalization', string='Hospitalization')


class PatientProcedure(models.Model):
    _inherit="acs.patient.procedure"

    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Inpatient')


class Physician(models.Model):
    _inherit = "hms.physician"

    def _hos_rec_count(self):
        Hospitalization = self.env['acs.hospitalization']
        for record in self.with_context(active_test=False):
            record.hospitalization_count = Hospitalization.search_count([('physician_id', '=', record.id)])

    hospitalization_count = fields.Integer(compute='_hos_rec_count', string='# Hospitalization')
    ward_round_service_id = fields.Many2one('product.product', domain=[('type','=','service')],
        string='Ward Round Service',  ondelete='cascade', help='Ward Round Product')

    def action_hospitalization(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_hospitalization.acs_action_form_inpatient")
        action['domain'] = [('physician_id','=',self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action
    
class AccountPayment(models.Model):
    _inherit = "account.payment"

    acs_hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Hospitalization',
        help="Enter the patient hospitalization code")