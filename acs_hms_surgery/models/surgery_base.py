# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class Anesthesia(models.Model):
    _name = "hms.anesthesia"
    _rec_name="name"
    _description = "Anesthesia"

    name = fields.Char('Anesthesia Name', required=True)


class PreOperativeCheckListTemplate(models.Model):
    _name="pre.operative.check.list.template"
    _description = "Pre Operative Checklist Template"

    name = fields.Char(string="Name", required=True)
    remark = fields.Char(string="Remarks")


class PreOperativeCheckList(models.Model):
    _name="pre.operative.check.list"
    _description = "Pre Operative Checklist"

    name = fields.Char(string="Name", required=True)
    is_done = fields.Boolean(string="Done")
    remark = fields.Char(string="Remarks")
    surgery_id = fields.Many2one("hms.surgery", ondelete="cascade", string="Surgery")


class ACSDietplan(models.Model):
    _name = "hms.dietplan"
    _description = "Diet plan"

    name = fields.Char(string='Name', required=True)


class PastSurgeries(models.Model):
    _name = "past.surgeries"
    _description = "Past Surgeries"

    result = fields.Char(string='Result')
    date = fields.Date(string='Date')
    hosp_or_doctor = fields.Char(string='Hospital/Doctor')
    description = fields.Char(string='Description', size=128)
    complication = fields.Text("Complication")
    patient_id = fields.Many2one('hms.patient', ondelete="restrict", string='Patient ID', help="Mention the past surgeries of this patient.")
