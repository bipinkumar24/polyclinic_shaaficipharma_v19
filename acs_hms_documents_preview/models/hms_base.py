# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class AcsHmsPatient(models.Model):
    _name="hms.patient"
    _inherit = ['hms.patient', 'acs.document.view.mixin']


class AcsHmsTreatment(models.Model):
    _name="hms.treatment"
    _inherit = ['hms.treatment', 'acs.document.view.mixin']


class AcsPatientProcedure(models.Model):
    _name="acs.patient.procedure"
    _inherit = ['acs.patient.procedure', 'acs.document.view.mixin']


class AcsHmsAppointment(models.Model):
    _name="hms.appointment"
    _inherit = ['hms.appointment', 'acs.document.view.mixin']

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: