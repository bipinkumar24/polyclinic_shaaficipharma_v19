# coding=utf-8
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ACSSurgeryTemplate(models.Model):
    _name = "hms.surgery.template"
    _description = "Surgery Template"

    name= fields.Char(string='Surgery Code', 
        help="Procedure Code, for example ICD-10-PCS Code 7-character string")
    surgery_name= fields.Char (string='Surgery Name')
    diseases_ids = fields.Many2many('hms.diseases', 'diseases_surgery_template_rel', 'diseas_id', 'surgery_id', string='Diseases')
    dietplan_id = fields.Many2one('hms.dietplan', ondelete='set null', string='Diet Plan')
    surgery_product_id = fields.Many2one('product.product', ondelete='cascade',
        string= "Product", required=True)
    diagnosis = fields.Text(string="Diagnosis")
    clinical_history = fields.Text(string="Clinical History")
    examination = fields.Text(string="Examination")
    investigation = fields.Text(string="Investigation")
    adv_on_dis = fields.Text(string="Advice on Discharge")
    notes = fields.Text(string='Operative Notes')
    classification = fields.Selection ([
        ('o','Optional'),
        ('r','Required'),
        ('u','Urgent')], string='Surgery Classification', index=True)
    extra_info = fields.Text (string='Extra Info')
    special_precautions = fields.Text(string="Special Precautions")
    consumable_line_ids = fields.One2many('hms.consumable.line', 'surgery_template_id', string='Consumable Line', help="List of items that are consumed during the surgery.")
    medicament_line_ids = fields.One2many('prescription.line', 'surgery_template_id', string='Medicament Line', help="Define the medicines to be taken after the surgery")
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital', default=lambda self: self.env.company)


class ACSSurgery(models.Model):
    _name = "hms.surgery"
    _description = "Surgery"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin', 'acs.calendar.mixin', 'barcodes.barcode_events_mixin', 'product.catalog.mixin']
    _order = "id desc"

    @api.model
    def _default_pre_checklist(self):
        vals = []
        pre_checklists = self.env['pre.operative.check.list.template'].search([])
        for rec in pre_checklists:
            vals.append((0,0,{
                'name': rec.name,
                'remark': rec.remark,
            }))
        return vals

    @api.depends('pre_operative_checklist_ids','pre_operative_checklist_ids.is_done')
    def _compute_checklist_done(self):
        for rec in self:
            if rec.pre_operative_checklist_ids:
                done_checklist = rec.pre_operative_checklist_ids.filtered(lambda s: s.is_done)
                rec.pre_operative_checklist_done = (len(done_checklist)* 100)/len(rec.pre_operative_checklist_ids)
            else:
                rec.pre_operative_checklist_done = 0

    @api.depends('patient_id')
    def _get_patient_age(self):
        for rec in self:
            if rec.patient_id:
                rec.age = rec.patient_id.age

    def _acs_rec_count(self):
        for rec in self:
            rec.invoice_count = len(self.invoice_ids)

    name = fields.Char(string='Surgery Number', copy=False, readonly=True,default='New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ('done', 'Done'),], string='Status', default='draft', tracking=1)
    surgery_name= fields.Char(string='Surgery Name', tracking=1)
    diseases_ids = fields.Many2many('hms.diseases', 'diseases_surgery_rel', 'diseas_id', 'surgery_id', string='Diseases')
    dietplan_id = fields.Many2one('hms.dietplan', ondelete='set null', 
        string='Diet Plan')
    surgery_product_id = fields.Many2one('product.product', ondelete='cascade',
        string= "Surgery Product", required=True)
    surgery_template_id = fields.Many2one('hms.surgery.template', ondelete='restrict',
        string= "Surgery Template", tracking=1)
    patient_id = fields.Many2one('hms.patient', ondelete="restrict", string='Patient', tracking=1)
    diagnosis = fields.Text(string="Diagnosis")
    clinical_history = fields.Text(string="Clinical History")
    examination = fields.Text(string="Examination")
    investigation = fields.Text(string="Investigation")
    adv_on_dis = fields.Text(string="Advice on Discharge")
    notes = fields.Text(string='Operative Notes')
    classification = fields.Selection ([
            ('o','Optional'),
            ('r','Required'),
            ('u','Urgent')
        ], string='Surgery Classification', index=True)
    age = fields.Char(string='Patient age',
        help='Patient age at the moment of the surgery. Can be estimative',compute='_get_patient_age' ,store=True)
    extra_info = fields.Text (string='Extra Info')
    special_precautions = fields.Text(string="Special Precautions")
    consumable_line_ids = fields.One2many('hms.consumable.line', 'surgery_id', string='Consumable Line', help="List of items that are consumed during the surgery.")
    medicament_line_ids = fields.One2many('prescription.line', 'surgery_id', string='Medicament Line', help="Define the medicines to be taken after the surgery")
    invoice_exempt = fields.Boolean(string='Invoice Exempt')

    #Hospitalization Surgery
    start_date = fields.Datetime(string='Surgery Date')
    end_date = fields.Datetime(string='End Date')
    anesthetist_id = fields.Many2one('hms.physician', string='Anesthetist', ondelete="set null", 
        help='Anesthetist data of the patient')
    anesthesia_id = fields.Many2one('hms.anesthesia', ondelete="set null", 
        string="Anesthesia")
    primary_physician_id = fields.Many2one('hms.physician', ondelete="restrict", 
        string='Main Surgeon')
    primary_physician_ids = fields.Many2many('hms.physician','hosp_pri_doc_rel','hosp_id','doc_id',
        string='Primary Surgeons')
    assisting_surgeon_ids = fields.Many2many('hms.physician','hosp_doc_rel','hosp_id','doc_id',
        string='Assisting Surgeons')
    scrub_nurse_id = fields.Many2one('res.users', ondelete="set null", 
        string='Scrub Nurse')
    pre_operative_checklist_ids = fields.One2many('pre.operative.check.list', 'surgery_id', 
        string='Pre-Operative Checklist', default=lambda self: self._default_pre_checklist())
    pre_operative_checklist_done = fields.Float('Pre-Operative Checklist Done', compute='_compute_checklist_done', store=True)
    notes = fields.Text(string='Operative Notes')
    post_instruction = fields.Text(string='Instructions')

    special_precautions = fields.Text(string="Special Precautions")
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital', default=lambda self: self.env.company)
    invoice_id = fields.Many2one('account.move', string='Invoice', copy=False)
    treatment_id = fields.Many2one('hms.treatment', string='Treatment', copy=False)
    department_id = fields.Many2one('hr.department', ondelete='restrict', 
        domain=lambda self: self.acs_get_department_domain(), string='Department', tracking=True)
    appointment_id = fields.Many2one('hms.appointment', string='Appointment', copy=False)
    invoice_ids = fields.One2many('account.move', 'surgery_id', string='Invoices')
    invoice_count = fields.Integer(compute='_acs_rec_count', string='# Invoices')

    def action_requestd(self):
        for record in self:
            record.write({'state': 'requested'})

    @api.onchange('surgery_template_id')
    def onchange_surgery_id(self):
        Consumable = self.env['hms.consumable.line']
        MedicamentLine = self.env['prescription.line']
        if self.surgery_template_id:
            self.surgery_name = self.surgery_template_id.surgery_name
            self.diseases_ids = self.surgery_template_id.diseases_ids
            self.surgery_product_id = self.surgery_template_id.surgery_product_id and self.surgery_template_id.surgery_product_id.id
            self.diagnosis = self.surgery_template_id.diagnosis
            self.clinical_history = self.surgery_template_id.clinical_history
            self.examination = self.surgery_template_id.examination
            self.investigation = self.surgery_template_id.investigation
            self.adv_on_dis = self.surgery_template_id.adv_on_dis
            self.notes = self.surgery_template_id.notes
            self.classification = self.surgery_template_id.classification

            for line in self.surgery_template_id.consumable_line_ids:
                self.consumable_line_ids += Consumable.new({
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id and line.product_uom_id.id or False,
                    'qty': line.qty,
                    'lot_id': line.lot_id and line.lot_id.id or False,
                })

            for line in self.surgery_template_id.medicament_line_ids:
                self.medicament_line_ids += MedicamentLine.new({
                    'product_id': line.product_id.id,
                    'common_dosage_id': line.common_dosage_id and line.common_dosage_id.id or False,
                    'dose': line.dose,
                    'active_component_ids': [(6, 0, [x.id for x in line.active_component_ids])],
                    'form_id' : line.form_id.id,
                    'quantity': line.quantity,
                    'days': line.days,
                    'manual_quantity': line.manual_quantity,
                    'qty_per_day': line.qty_per_day,
                    'instruction': line.instruction,
                })

    def acs_prepare_calendar_data(self):
        data = super().acs_prepare_calendar_data()
        user_id = self.primary_physician_id.user_id
        partner_ids = [user_id.partner_id.id]
        for dr in self.primary_physician_ids:
            partner_ids.append(dr.partner_id.id)
        for dr in self.assisting_surgeon_ids:
            partner_ids.append(dr.partner_id.id)
        if self.anesthetist_id:
            partner_ids.append(self.anesthetist_id.partner_id.id)
        
        data.update({
            'user_id': user_id.id,
            'start': self.start_date,
            'stop': self.end_date,
            'partner_ids': [(6, 0, partner_ids)],
        })
        return data
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                seq_date = None
                if vals.get('start_date'):
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['start_date']))
                vals['name'] = self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code('hms.surgery', sequence_date=seq_date) or _("New")
        res = super().create(vals_list)
        for record in res:
            record.acs_calendar_event('primary_physician_id')
        return res   
         
    def write(self, values):
        res = super().write(values)
        fields_to_check = ['start_date','end_date','primary_physician_id','primary_physician_ids','assisting_surgeon_ids','anesthetist_id','state']
        if any(f in values for f in fields_to_check):
            self.acs_calendar_event('primary_physician_id')
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for record in self:
            if record.state not in ('draft', 'cancel'):
                raise UserError(_("You can delete a record in draft or cancelled state only."))

    def action_confirm(self):
        self.state = 'confirm'

    def action_done(self):
        self.state = 'done'
        self.acs_consume_material('surgery_id')

    def action_cancel(self):
        self.state = 'cancel'

    def action_draft(self):
        self.state = 'draft'

    def acs_get_consume_locations(self):
        if not self.company_id.acs_surgery_usage_location_id:
            raise UserError(_('Please define a location where the consumables will be used in settings.'))
        if not self.company_id.acs_surgery_stock_location_id:
            raise UserError(_('Please define a surgery location from where the consumables will be taken.'))
        source_location_id  = self.company_id.acs_surgery_stock_location_id.id
        dest_location_id  = self.company_id.acs_surgery_usage_location_id.id
        return source_location_id, dest_location_id

    def get_surgery_invoice_data(self):
        product_data = [{
            'name': _("Surgery Charges"),
        }]
        for surgery in self:
            if surgery.invoice_exempt:
                continue

            if surgery.surgery_product_id:
                #Line for Surgery Charge
                product_data.append({
                    'product_id': surgery.surgery_product_id,
                    'quantity': 1,
                    'line_type': 'surgery'
                })

            #Line for Surgery Consumables
            for surgery_consumable in surgery.consumable_line_ids:
                product_data.append({
                    'product_id': surgery_consumable.product_id,
                    'quantity': surgery_consumable.qty,
                    'lot_id': surgery_consumable.lot_id and surgery_consumable.lot_id.id or False,
                    'product_uom_id': surgery_consumable.product_uom_id.id,
                    'line_type': 'surgery'
                })
        return product_data

    def action_create_invoice(self):
        product_data = self.get_surgery_invoice_data()
        inv_data = {
            'physician_id': self.primary_physician_id and self.primary_physician_id.id or False,
            'hospital_invoice_type': 'surgery',
        }
        acs_context = {'commission_partner_ids':self.primary_physician_id.partner_id.id}
        invoice_id = self.with_context(acs_context).acs_create_invoice(partner=self.patient_id.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        invoice_id.write({
            'surgery_id': self.id,
        })
        self.invoice_id = invoice_id.id
        return invoice_id

    def action_prescription(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.act_open_hms_prescription_order_view")
        action['domain'] = [('surgery_id', '=', self.id)]
        action['context'] = {
                'default_patient_id': self.patient_id.id,
                'default_diseases_ids': [(6,0,self.diseases_ids.ids)],
                'default_surgery_id': self.id}
        return action

    def view_invoice(self):
        invoices = self.env['account.move'].search([('surgery_id', '=', self.id)])
        action = self.acs_action_view_invoice(invoices)
        return action

    def acs_create_prescription(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.act_open_hms_prescription_order_view")        
        action['domain'] = [('surgery_id', '=', self.id)]
        action['views'] = [(self.env.ref('acs_hms.view_hms_prescription_order_form').id, 'form')]
        medicament_lines = []

        for line in self.medicament_line_ids:
            medicament_lines.append((0,0,{
                'product_id': line.product_id.id,
                'common_dosage_id': line.common_dosage_id and line.common_dosage_id.id or False,
                'dose': line.dose,
                'active_component_ids': [(6, 0, [x.id for x in line.active_component_ids])],
                'form_id' : line.form_id.id,
                'quantity': line.quantity,
                'days': line.days,
                'manual_quantity': line.manual_quantity,
                'qty_per_day': line.qty_per_day,
                'short_comment': line.instruction,
            }))

        action['context'] = {
                'default_patient_id': self.patient_id.id,
                'default_diseases_ids': [(6,0,self.diseases_ids.ids)],
                'default_treatment_id': self.treatment_id and self.treatment_id.id or False,
                'default_surgery_id': self.id,
                'default_prescription_line_ids': medicament_lines}
        return action

    #method to create get invoice data and set passed invoice id.
    def acs_common_invoice_surgery_data(self, invoice_id=False):
        data = []
        if self.ids:
            data = self.get_surgery_invoice_data()
            if invoice_id:
                self.invoice_id = invoice_id.id
        return data
    
    # method to scan products with barcode or lot numbers
    def on_barcode_scanned(self, barcode):
        if barcode and self.state=='draft':
            lot = False
            ProductObj = self.env['product.product']
            Lot = self.env['stock.lot']

            product = ProductObj.search([('barcode','=',barcode)], limit=1)
            if not product:
                lot = Lot.search([('name', '=', barcode)], limit=1)
                product = lot.product_id
            if not product and not lot:
                raise UserError(_('There is no product with Barcode or Reference or Lot: %s') % (barcode))

            flag = True
            if product and not lot:
                for o_line in self.consumable_line_ids:
                    if o_line.product_id == product and not o_line.lot_id:
                        o_line.qty += 1
                        flag = False
                        break
            elif lot:
                for o_line in self.consumable_line_ids:
                    if o_line.product_id == product and o_line.lot_id == lot:
                        o_line.qty += 1
                        flag = False
                        break
            if flag:
                self.consumable_line_ids = [(0, 0, {
                    'product_id': product.id,
                    'price_unit': product.lst_price,
                    'name':product.name,
                    'qty': 1,
                    'lot_id': lot.id if lot else False,
                    'product_uom_id': product.uom_id.id,
                })]

    # This method updates or adds a consumable line for the given product and quantity using a common helper function.
    def _update_order_line_info(self, product_id, quantity, **kwargs):
        return self.acs_generic_update_order_line_info(model='hms.consumable.line', product_id=product_id, quantity=quantity,link_field='surgery_id', extra_vals={'physician_id': self.primary_physician_id.id})
