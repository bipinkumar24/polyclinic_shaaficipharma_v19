from odoo import models, fields, api
from odoo.exceptions import UserError

class AppointmentInvoiceWizard(models.TransientModel):
    _name = 'appointment.invoice.wizard'
    _description = 'Create Invoice Wizard'

    appointment_id = fields.Many2one('hms.appointment')

    insurance_type = fields.Selection([
        ('no', 'No Insurance'),
        ('full', 'Full Insurance'),
        ('partial', 'Partial Insurance'),
    ], string="Insurance Type", default="no")

    insurance_company_id = fields.Many2one('hms.insurance.company', string="Insurance Company")
    line_ids = fields.One2many(
        'appointment.invoice.wizard.line',
        'wizard_id',
        string="Products"
    )

    total_amount = fields.Float(compute="_compute_total")

    insurance_amount = fields.Float(string="Insurance Amount")

    patient_amount = fields.Float(
        compute="_compute_patient_amount",
        string="Patient Pay Amount"
    )

    @api.onchange('insurance_type', 'line_ids')
    def _chcek_amount_type(self):
        if self.insurance_type == 'full':
           self.insurance_amount = self.total_amount

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))

    @api.depends('total_amount', 'insurance_amount')
    def _compute_patient_amount(self):
        for rec in self:
            rec.patient_amount = rec.total_amount - rec.insurance_amount


    def action_create_invoice(self):
        appointment = self.appointment_id
        if not appointment:
            raise UserError("Appointment not found.")
        if self.total_amount == 0:
            raise UserError("Invoice not Create 0 Amount")


        invoice_lines = []
        grouped_lines = {}
        # Group lines by hospital_product_type
        for line in self.line_ids:
            key = line.product_id.hospital_product_type
            grouped_lines.setdefault(key, []).append(line)

        for product_type, lines in grouped_lines.items():
            if product_type:
                section_name = product_type.replace('_', ' ').title() + " Charges"
                invoice_lines.append((0, 0, {
                    'display_type': 'line_section',
                    'name': section_name,
                }))
            for line in lines:
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                }))


        product_data = []
        inv_data = appointment.acs_appointment_inv_data()
        acs_context = {'commission_partner_id': appointment.physician_id.partner_id.id}
        if appointment.pricelist_id:
            acs_context.update({'acs_pricelist_id': appointment.pricelist_id.id})
            
        invoice = appointment.with_context(acs_context).acs_create_invoice(
            partner=appointment.patient_id.partner_id, 
            patient=appointment.patient_id, 
            product_data=product_data, 
            inv_data=inv_data
        )
        
        # Link invoice directly
        appointment.write({
            'invoice_id': invoice.id,
            'invoice_ids': [(4, invoice.id)]
        })
        invoice.write({
            'invoice_line_ids': invoice_lines
        })

        if appointment.state == 'to_invoice':
            appointment.appointment_done()

        if appointment.state == 'draft' and not appointment._context.get('avoid_confirmation'):
            if appointment.invoice_id and not appointment.company_id.acs_check_appo_payment:
                appointment.appointment_confirm()
        
        req_ids = appointment.mapped('radiology_request_ids').filtered(lambda req: not req.invoice_id)
        lab_request_ids = appointment.mapped('lab_request_ids').filtered(lambda req: not req.invoice_id)
        surgery_ids = appointment.surgery_ids.filtered(lambda s: not s.invoice_id)
        # prescription_ids = appointment.mapped('prescription_ids').filtered(lambda req: req.state == 'prescription' and not req.invoice_id)
        vaccination_ids = appointment.mapped('vaccination_ids').filtered(lambda req: not req.invoice_id)
        patient_procedure_ids = appointment.mapped('patient_procedure_ids').filtered(lambda req: not req.invoice_id)
        
        # Changed if-elif-elif chain to independent if statements (can have multiple requests)
        # Fixed NameError from 'invoice_id' and name shadowing of 'invoice' variable
        if req_ids:
            invoice.write({'radiology_request_move_ids': [(4, req.id) for req in req_ids]})
            req_ids.write({'invoice_id': invoice.id})

        if lab_request_ids:
            invoice.write({'lab_request_move_ids': [(4, req.id) for req in lab_request_ids]})
            lab_request_ids.write({'invoice_id': invoice.id})

        if surgery_ids:
            invoice.write({'surgery_request_move_ids': [(4, req.id) for req in surgery_ids]})
            surgery_ids.write({'invoice_id': invoice.id})

        # if prescription_ids:
        #     prescription_ids.write({'invoice_id': invoice.id})

        if patient_procedure_ids:
            invoice.write({'procedure_request_move_ids': [(4, req.id) for req in patient_procedure_ids]})
            surgery_ids.write({'invoice_id': invoice.id})

        if vaccination_ids:
            vaccination_ids.write({'invoice_id': invoice.id})
        if appointment.is_charge_the_appoinmnet_fee:
            appointment.is_invoice = True
        else:
            appointment.is_invoice = False

        if appointment.invoice_id and self.insurance_type != 'no' and self.insurance_amount != 0:
            subtotal_amount = self.total_amount
            insurance_balance = self.patient_amount
            card_insurance_company_id = self.insurance_company_id.partner_id
            
            if subtotal_amount >= insurance_balance:
                patient_amount = min(subtotal_amount, insurance_balance)
            else:
                patient_amount = self.patient_amount
            
            data = {
                'card_insurance_company_id': card_insurance_company_id,
                'available_insurancecard_balance': True,
                'patient_amount': patient_amount,
                'acs_object': appointment,
                'inv_type': 'appointment',
                'rec_field': 'appointment_id',
                'line_ids': self.line_ids if self.insurance_type != 'full' else False,
                'insurance_amount': self.insurance_amount
            }
            insurance_invoice = appointment.invoice_id.acs_create_insurance_card_invoice(**data)

class AppointmentInvoiceWizardLine(models.TransientModel):
    _name = 'appointment.invoice.wizard.line'

    wizard_id = fields.Many2one('appointment.invoice.wizard')

    product_id = fields.Many2one('product.product', required=True)

    quantity = fields.Float(default=1)

    price_unit = fields.Float()

    subtotal = fields.Float(compute="_compute_subtotal")

    @api.depends('quantity','price_unit')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.price_unit