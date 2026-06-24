# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo import fields as odoo_fields, http, tools, _, SUPERUSER_ID
import json


class ACSDentalChart(http.Controller):

    def acs_procedures_data(self, patient, post={}):
        upper_teeths = request.env['acs.hms.tooth'].search([], limit=16, offset=0)
        lower_teeths = request.env['acs.hms.tooth'].search([], limit=16, offset=16)
        lower_teeths = request.env['acs.hms.tooth'].search([('id','in',lower_teeths.ids)], order="id desc")
        surfaces =  request.env['acs.tooth.surface'].search([])
        procedures =  request.env['product.product'].search([('hospital_product_type','=','dental_procedure')])
        treatment = post.get('treatment_id')
        if not treatment:
            treatments = patient.treatment_ids.filtered(lambda t: t.department_id.department_type=='dental' and t.state=='running')
            if treatments:
                treatment = treatments[0].id
        patient_procedure_ids = patient.patient_procedure_ids.filtered(lambda t: (t.department_id.department_type=='dental' or t.tooth_ids) and (t.state in ['scheduled','running'] or not t.invoice_id))
        patient_procedure_done_ids = patient.patient_procedure_ids.filtered(lambda t: (t.department_id.department_type=='dental' or t.tooth_ids) and t.state in ['done'])
        data = {
            'error_message': post.get('error_message',''),
            'sucess_message': post.get('sucess_message',''),
            'treatment_id': treatment, 
            'appointment_id': post.get('appointment_id'),
            'acs_header_invisible': True, 
            'acs_footer_invisible': True, 
            'lower_teeths': lower_teeths,
            'upper_teeths': upper_teeths,
            'surfaces': surfaces,
            'procedures': procedures,
            'patient': patient,
            'acs_teeth_json_data': json.loads(patient.acs_teeth_json_data),
            'patient_procedure_ids': patient_procedure_ids,
            'patient_procedure_done_ids': patient_procedure_done_ids,
            'currency_id': request.env.user.sudo().company_id.currency_id,
        }
        return data

    @http.route(['/acs/dental/<int:patient_id>'], type='http', auth="user", website=True, sitemap=False)
    def patient_dental_procedure(self, patient_id=None, access_token=None, **kw):
        patient = request.env['hms.patient'].search([('id','=',patient_id)])
        if not patient:
            return request.render("acs_hms_dental_chart.acs_no_details")
        data = self.acs_procedures_data(patient, kw)
        return request.render("acs_hms_dental_chart.acs_dental_procedure", data)

    @http.route(['/acs/create/dental/procedure'], type='http', auth='user', website=True, sitemap=False)
    def acs_create_procedure(self, redirect=None, **post):
        user = request.env.user.sudo()
        patient = request.env['hms.patient'].sudo().search([('id','=',post.get('patient_id'))])
        data = self.acs_procedures_data(patient)

        #Check Data error
        error_message = ''
        selected_teeth = []
        for rec in post:
            vals = rec.split('acs_tooth-')
            if len(vals)==2:
                selected_teeth.append(int(vals[1]))
        if not selected_teeth:
            error_message += ' ' + _('Please Select Tooth and other data Properly.')
        if not post.get('product_id'):
            error_message += ' ' + _('Please Select Procedure and other data Properly.')

        if error_message:
            data.update({'error_message': error_message})
            return request.redirect("/acs/dental/%s?error_message=%s"  % (patient.id, error_message))

        selected_surfaces = []
        for rec in post:
            vals = rec.split('surface_')
            if len(vals)==2:
                selected_surfaces.append(int(vals[1]))

        department = request.env['hr.department'].search([('department_type','=','dental')], limit=1)
        if department:
            department = department.id

        product_id = request.env['product.product'].sudo().search([('id','=',post.get('product_id'))])
        procedure_data = {
            'patient_id': patient.id,
            'treatment_id': post.get('treatment_id'),
            'product_id': product_id.id,
            'tooth_ids': [(6,0,selected_teeth)],
            'tooth_surface_ids': [(6,0,selected_surfaces)],
            'physician_id': user.physician_ids and user.physician_ids[0].id or False,
            'department_id': department,
            'price_unit': product_id.list_price,
            'date': fields.Datetime.now(),
        }
        if post.get('appointment_id'):
            procedure_data.update({
                'appointment_ids': [(6,0,[post.get('appointment_id', False)])]
            })

        # Create Procedure
        procedure_id = request.env['acs.patient.procedure'].sudo().create(procedure_data)
        sucess_message = _('Created new Procedure %s.') % (procedure_id.name)
        return request.redirect("/acs/dental/%s?sucess_message=%s"  % (patient.id, sucess_message))

    @http.route(['/acs/update/procedure/<int:procedure_id>'], type='http', auth="user", website=True, sitemap=False)
    def acs_delete_procedure(self, procedure_id=None, access_token=None, **kw):
        procedure_id = request.env['acs.patient.procedure'].search([('id','=',procedure_id)])
        patient = procedure_id.patient_id
        if procedure_id:
            if kw.get('action')=='createinvoice' and not procedure_id.invoice_id:
                procedure_id.action_create_invoice()
            if kw.get('action')=='delete' and procedure_id.state=='scheduled':
                procedure_id.unlink()
            elif kw.get('action')=='inprogress' and procedure_id.state=='scheduled':
                procedure_id.action_running()
            elif kw.get('action')=='done' and procedure_id.state=='running':
                procedure_id.action_done()
        return request.redirect("/acs/dental/%s"  % (patient.id))
    
    @http.route(['/acs/procedure/notes'], type='jsonrpc', auth="user", methods=['POST'], website=True)
    def acs_update_procedure_notes(self, **kw):
        procedure_id = request.env['acs.patient.procedure'].search([('id','=',kw.get('procedure_id'))])
        procedure_id.notes = kw.get('notes')
        return {'success': True}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: