# coding: utf-8

from odoo import models, api, fields, _
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError


class AcsHmsInvoice(models.Model):
    _name = 'acs.hms.invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin']
    _description = "Patient Invoice"
    _order = "id desc"

    @api.depends('line_ids.price_total', 'appointment_ids', 'surgery_ids', 'procedure_ids', 'vaccination_ids')
    def acs_get_total(self):
        """
        Compute the total amounts of the order.
        """
        for rec in self:
            amount_untaxed = amount_tax = 0.0
            for line in rec.line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            rec.update({
                'amount_untaxed': rec.company_id.currency_id.round(amount_untaxed),
                'amount_tax': rec.company_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'appointment_total': sum(rec.line_ids.filtered(lambda l: l.line_type=='appointment').mapped('price_total')),
                'surgery_total': sum(rec.line_ids.filtered(lambda l: l.line_type=='surgery').mapped('price_total')),
                'procedure_total': sum(rec.line_ids.filtered(lambda l: l.line_type=='procedure').mapped('price_total')),
                'hospitalization_total': sum(rec.line_ids.filtered(lambda l: l.line_type=='hospitalization').mapped('price_total')),
                'vaccination_total': sum(rec.line_ids.filtered(lambda l: l.line_type=='vaccination').mapped('price_total')),
            })

    name = fields.Char(string='Name', required=True, readonly=True, default='New', copy=False)

    patient_id = fields.Many2one('hms.patient', string="Patient")
    patient_mobile = fields.Char(related="patient_id.mobile", string="Mobile")
    patient_age = fields.Char(related="patient_id.age", string="Age")
    partner_id = fields.Many2one('res.partner', related="patient_id.partner_id", string="Partner")

    date = fields.Date(string="Date", default=fields.Date.today())

    payment_journal_id = fields.Many2one('account.journal', string='Payment Method', domain="[('type','=','cash')]")
    user_id = fields.Many2one('res.users', string='User',  required=True, default=lambda self: self.env.user)

    appointment_ids = fields.Many2many('hms.appointment', 'acs_hms_invoice_appointment_rel', 'appointment_id', 'hms_inv_id', string='Appointments')
    surgery_ids = fields.Many2many('hms.surgery', 'acs_hms_invoice_surgery_rel', 'surgery_id', 'hms_inv_id', string='Surgeries')
    procedure_ids = fields.Many2many('acs.patient.procedure', 'acs_hms_invoice_procedure_rel', 'procedure_id', 'hms_inv_id', string='Procedures')
    hospitalization_ids = fields.Many2many('acs.hospitalization', 'acs_hms_invoice_hospitalization_rel', 'hospitalization_id', 'hms_inv_id', string='Hospitalizations')
    vaccination_ids = fields.Many2many('acs.vaccination', 'acs_hms_invoice_vaccination_rel', 'vaccination_id', 'hms_inv_id', string='Vaccinations')

    discount_type = fields.Selection([('fixed','Fixed'),('percentage','Percentage')], "Discount Type")
    discount_amount = fields.Float("Discount Amount")
    discount_percentage = fields.Float("Discount Percentage")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('done', 'Done'),
    ], string='Status',default='draft', required=True, copy=False, tracking=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', copy=False)
    line_ids = fields.One2many("acs.hms.invoice.line", 'order_id', string='Forecast Lines', readonly=False, copy=True)

    appointment_total = fields.Float(compute="acs_get_total", string="Appointment Total Amount", store=True)
    procedure_total = fields.Float(compute="acs_get_total", string="Procedure Total Amount", store=True)
    surgery_total = fields.Float(compute="acs_get_total", string="Surgery Total Amount", store=True)
    hospitalization_total = fields.Float(compute="acs_get_total", string="Hospitalization Total Amount", store=True)
    vaccination_total = fields.Float(compute="acs_get_total", string="Vaccination Total Amount", store=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='acs_get_total')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='acs_get_total')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='acs_get_total')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", related='company_id.currency_id', string="Currency", readonly=True, required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                seq_date = None
                if vals.get('date'):
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
                vals['name'] = self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code('acs.hms.invoice', sequence_date=seq_date) or _("New")
        res=super().create(vals_list)
        for record in res:
            record.acs_get_patient_data() 
        return res
    
    def view_invoice(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['domain'] = [('id','=',self.invoice_id.id)]
        return action

    def acs_get_patient_data(self):
        Line = self.env['acs.hms.invoice.line']
        if self.patient_id:
            appointments = self.env['hms.appointment'].search([('patient_id','=',self.patient_id.id),('invoice_id','=',False),('state','=','to_invoice')])
            self.appointment_ids = [(6,0,appointments.ids)]

            procedures = self.env['acs.patient.procedure'].search([('patient_id','=',self.patient_id.id),('invoice_id','=',False),('state','in',['scheduled'])])
            self.procedure_ids = [(6,0,procedures.ids)]

            surgeries = self.env['hms.surgery'].search([('patient_id','=',self.patient_id.id),('invoice_id','=',False),('state','=','draft')])
            self.surgery_ids = [(6,0,surgeries.ids)]
            
            hospitalizations = self.env['acs.hospitalization'].search([('patient_id','=',self.patient_id.id),('invoice_ids','=',False),('state','=','discharged')])
            self.hospitalization_ids = [(6,0,hospitalizations.ids)]

            vaccinations = self.env['acs.vaccination'].search([('patient_id','=',self.patient_id.id),('invoice_id','=',False),('state','=','to_invoice')])
            self.vaccination_ids = [(6,0,vaccinations.ids)]

            data = []
            self.line_ids.unlink()
            for appointment in self.appointment_ids:
                data += appointment.acs_appointment_inv_product_data()
            
            for surgery in self.surgery_ids:
                data += surgery.get_surgery_invoice_data()
            
            for procedure in self.procedure_ids:
                data += procedure.get_procedure_invoice_data()
            
            for hospitalization in self.hospitalization_ids:
                data += hospitalization.get_hospitalization_invoice_data()
            
            for vaccination in self.vaccination_ids:
                data += vaccination.get_acs_vaccination_invoice_data()
            
            fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(self.patient_id.partner_id)

            sequence = 1
            for product_data in data:
                sequence += 1
                product = product_data.get('product_id')
                if product:
                    acs_pricelist_id = self.pricelist_id.id or self.env.context.get('acs_pricelist_id')
                    if not product_data.get('price_unit') and (self.partner_id.property_product_pricelist or acs_pricelist_id):
                        if acs_pricelist_id:
                            pricelist_id = self.env['product.pricelist'].browse(acs_pricelist_id)
                        else:
                            pricelist_id = self.partner_id.property_product_pricelist
                        price = pricelist_id._get_product_price(product, product_data.get('quantity',1.0))
                    else:
                        price = product_data.get('price_unit', product.list_price)
                    
                    tax_ids = product.taxes_id
                    if tax_ids:
                        if fiscal_position_id:
                            tax_ids = fiscal_position_id.map_tax(tax_ids._origin)
                        tax_ids = [(6, 0, tax_ids.ids)]
                    line = Line.create({
                        'order_id': self.id,
                        'name': product_data.get('name',product.get_product_multiline_description_sale()),
                        'product_id': product.id,
                        'price_unit': price,
                        'quantity': product_data.get('quantity',1.0),
                        'discount': product_data.get('discount',0.0),
                        'product_uom_id': product_data.get('product_uom_id',product.uom_id.id),
                        'tax_ids': tax_ids,
                        'sequence': sequence,
                        'line_type': product_data.get('line_type')
                    })
                else:
                    line = Line.create({
                        'order_id': self.id,
                        'name': product_data.get('name'),
                        'display_type': 'line_section',
                        'sequence': sequence,
                    })
                    
            #Discount line
            amount = 0
            if self.discount_type == 'fixed':
                amount = self.discount_amount
            elif self.discount_type == 'percentage':
                amount = (self.amount_untaxed * self.discount_percentage)/100

            if amount:
                acs_product_id = self.env.user.sudo().company_id.invoice_discount_product_id
                if not acs_product_id:
                    raise UserError(_('Please set Invoice Discount product in General Settings first.'))
                
                Line.create({
                    'order_id': self.id,
                    'product_id': acs_product_id.id,
                    'name': acs_product_id.name,
                    'price_unit': -amount,
                })

    def acs_create_invoice_record(self):
        partner = self.patient_id.partner_id
        patient = self.patient_id

        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'patient_id': patient and patient.id,
            'move_type': 'out_invoice',
            'currency_id': self.env.user.company_id.currency_id.id,
        })
        invoice._onchange_partner_id()

        for line in self.line_ids:
            product_data = {
                'name': line.name,
                'product_id': line.product_id,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'discount': line.discount,
                'product_uom_id': line.product_uom_id.id,
                'tax_ids': line.tax_ids.id,
                'sequence': line.sequence,
                'display_type': line.display_type
            }
            self.acs_create_invoice_line(product_data, invoice)

        for appointment in self.appointment_ids:
            appointment.appointment_confirm()
            appointment.invoice_id = invoice
            appointment.invoice_ids = [(6,0,invoice.ids)]

        for surgery in self.surgery_ids:
            surgery.action_confirm()
            surgery.invoice_id = invoice.id
            surgery.invoice_ids = [(6,0,invoice.ids)]
            
        for procedure in self.procedure_ids:
            procedure.action_running()
            procedure.invoice_id = invoice.id
            
        for hospitalization in self.hospitalization_ids:
            hospitalization.invoice_ids = [(6,0,invoice.ids)]

        for line in invoice.invoice_line_ids:
            line._get_computed_taxes()
        if invoice.invoice_line_ids:
            invoice.action_post()
        self.invoice_id = invoice.id
        self.state = 'done'
        return invoice

    def acs_create_invoice(self):
        invoice = self.acs_create_invoice_record()
        invoice.acs_action_cash_payment(payment_journal=self.payment_journal_id)
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = invoice.id
        return action

    def action_cancel(self):
        self.state = 'cancel'
    
    def action_reset_to_draft(self):
        self.state = 'draft'


class AcsHmsInvoiceLine(models.Model):
    _name = 'acs.hms.invoice.line'
    _description = "Patient Invoice Line"
    _order = "sequence, id"

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids')
    def _compute_amount(self):
        """
        Compute the amounts of the line.
        """
        for line in self:
            if not line.display_type:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.compute_all(price, line.order_id.currency_id, line.quantity, product=line.product_id, partner=line.order_id.create_uid.partner_id)
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })
            else:
                line.price_tax = 0
                line.price_total = 0
                line.price_subtotal = 0

    order_id = fields.Many2one('acs.hms.invoice', string='Order', required=True, ondelete='cascade', index=True, copy=False)
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict')
    quantity = fields.Float(string='Quantity', digits=('Product Unit of Measure'), default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float()
    discount = fields.Float()
    tax_ids = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Taxes Amount', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    currency_id = fields.Many2one(related='order_id.company_id.currency_id', store=True, string='Currency', readonly=True)
    display_type = fields.Selection([
        ('line_section', "Section")], help="Technical field for UX purpose.")
    line_type = fields.Selection([
        ('appointment', "Appointment"),
        ('surgery', "Surgery"),
        ('procedure', "Procedure"),
        ('hospitalization', "Hospitalization")])