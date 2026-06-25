# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
 
class SplitInvoiceLine(models.TransientModel):
    _name = 'split.invoice.line'
    _description = 'Split Record Line'

    wizard_id = fields.Many2one("split.invoice.wizard")
    line_id = fields.Many2one("account.move.line")
    product_id = fields.Many2one("product.product", "Product")
    name = fields.Text("Description")
    quantity = fields.Float("Quantity")
    price = fields.Float("Unit Price")
    qty_to_split = fields.Float(string='Split Qty')
    price_to_split = fields.Float(string='Split Price')
    percentage_to_split = fields.Float(string='Split Percentage')
    display_type = fields.Selection(related="line_id.display_type", help="Technical field for UX purpose.")
    full_cover = fields.Boolean(string="100%")


class SplitInvoiceWizard(models.TransientModel):
    _name = 'split.invoice.wizard'
    _description = 'Split Invoice Record'

    split_selection = fields.Selection([
            ('invoice','By Invoice'),
            ('lines','Invoice Lines'),
        ], 'Split By', default='invoice', required=True)
    line_split_selection = fields.Selection([
            ('qty','Quantity'),
            ('price','Unit Price'),
            ('percentage','Percentage'),
        ], 'Split Line by', default='qty')
    invoice_split_type = fields.Selection([
            ('full','Full Invoice'),
            ('new_line','Add New Line')
        ], 'Split Type', default='full', help="""1>Full Invoice: it will split invoice as it is. 
        2>Add New Line: split invoice by adding one new line only.""")
    invoice_split_by = fields.Selection([
            ('fixamount','Fix Amount'),
            ('percentage','Percentage'),
        ], 'Split Invoice By', default='percentage')
    percentage = fields.Float("Percentage to Split", default=50)
    fixamount = fields.Float("Amount to Split", default=50)
    split_product_id = fields.Many2one('product.product', 'Split Product')
    line_ids = fields.One2many('split.invoice.line', 'wizard_id', string='Invoice Lines')
    partner_id = fields.Many2one('res.partner', 'Customer/Supplier', required=True)
    update_partner = fields.Boolean('Update Partner', default=False)

    @api.model
    def default_get(self, fields):
        res = super(SplitInvoiceWizard, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        if active_model == 'account.move':
            active_record = self.env['account.move'].browse(self.env.context.get('active_id'))
            if active_record.state!='draft':
                raise ValidationError(_('Invoice must be in draft state.'))
            lines = []
            for line in active_record.invoice_line_ids:
                lines.append((0,0,{
                    'name': line.name,
                    'product_id': line.product_id and line.product_id.id or False,
                    'line_id': line.id,
                    'quantity': line.quantity,
                    'price': line.price_unit,
                    'qty_to_split': 1,
                    'price_to_split': line.price_unit * 0.5,
                    'percentage_to_split': 50,
                    'display_type': line.display_type,
                    'wizard_id': self.id
                }))
            res.update({'line_ids': lines, 'partner_id': active_record.partner_id.id })
        return res        

    def split_lines(self, active_record, split_field, update_field):
        lines_to_split = active_record.invoice_line_ids.filtered(lambda r: r[split_field] or r.full_cover)
        new_inv_id = False
        if len(lines_to_split) >= 1:
            new_inv_id = active_record.with_context(from_split_invoice=True).copy()
            new_inv_id.partner_id = self.partner_id.id
            for line in new_inv_id.invoice_line_ids:
                if not line[split_field] or line.full_cover:
                    line.with_context(check_move_validity=False).unlink()
                else:
                    line.with_context(check_move_validity=False).write({
                        update_field: line[split_field],
                        split_field: 0
                    })

            for line in active_record.invoice_line_ids:
                if line[split_field]:
                    if line[update_field] == line[split_field]:
                        line.with_context(check_move_validity=False).unlink()
                    else:
                        value = line[update_field] - line[split_field]
                        if line.full_cover:
                            value = line[update_field]
                        line.with_context(check_move_validity=False).write({
                            update_field: value,
                            split_field: 0
                        })
        else:
            raise ValidationError(_('Please Enter Proper Amount/Quantity/Percentage To Split.'))
        return new_inv_id

    #To manage label in relate module manage in separate method
    def split_record_full_inv_new_line_section(self, invoice):
        self.env['account.move.line'].with_context(check_move_validity=False).create({
            'move_id': invoice.id,
            'name': _("Split Share"),
            'display_type': 'line_section',
        })

    def acs_create_new_invoice_line(self, invoice, product_id, amount):
        account_id = product_id.property_account_income_id or product_id.categ_id.property_account_income_categ_id
        new_inv_line = self.env['account.move.line'].with_context(check_move_validity=False).create({
            'move_id': invoice.id,
            'name': product_id.get_product_multiline_description_sale(),
            'product_id': product_id.id,
            'account_id': account_id.id,
            'price_unit': amount,
            'quantity': 1,
            'discount': 0,
            'product_uom_id': product_id.uom_id.id,
            'display_type': 'product',
        })
        return new_inv_line

    def split_record(self): 
        active_model = self.env.context.get('active_model')
        new_inv_id = False
        active_record = False
        MoveLine = self.env['account.move.line']
        if active_model == 'account.move':
            active_record = self.env['account.move'].browse(self.env.context.get('active_id'))
            #Create Split Record
            if self.split_selection == 'invoice':
                #Incase of 100% just return active record and update partner.
                if (self.invoice_split_by=='percentage' and self.percentage==100) or \
                    (self.invoice_split_by=='fixamount' and \
                        (self.fixamount==active_record.amount_total or self.fixamount==0)):
                    active_record.write({'partner_id': self.partner_id.id})
                    active_record.with_context(check_move_validity=False)._onchange_partner_id()
                    return active_record, new_inv_id

                if self.invoice_split_by=='percentage' and not self.percentage:
                    raise ValidationError(_('Please Enter Percentage To Split.'))

                if self.invoice_split_by=='fixamount' and not self.fixamount:
                    raise ValidationError(_('Please Enter Amount To Split.'))

                if self.invoice_split_type == 'full':
                    if self.invoice_split_by=='fixamount':
                        raise ValidationError(_('On full invoice fix amount split is not supported.'))
                    new_inv_id = active_record.with_context(from_split_invoice=True).copy()
                    new_inv_id.partner_id = self.partner_id.id

                    for line in new_inv_id.invoice_line_ids:
                        new_price = line.price_unit * (self.percentage / 100)
                        line.with_context(check_move_validity=False).price_unit = new_price

                    for active_line in active_record.invoice_line_ids:
                        new_price = active_line.price_unit - (active_line.price_unit * (self.percentage / 100))
                        active_line.with_context(check_move_validity=False).price_unit = new_price
                else:
                    new_inv_id = active_record.with_context(from_split_invoice=True).copy()
                    if active_record.radiology_request_id:
                        new_inv_id.radiology_request_id = active_record.radiology_request_id
                    if active_record.request_id:
                        new_inv_id.request_id = active_record.request_id
                    
                    new_inv_id.partner_id = self.partner_id.id

                    if self.invoice_split_by=='percentage':
                        amount = (self.percentage * active_record.amount_total) / 100

                    if self.invoice_split_by=='fixamount':
                        amount = self.fixamount

                    split_product_id = self.split_product_id
                    if not split_product_id:
                        inv_product_ids = active_record.invoice_line_ids.mapped('product_id')
                        split_product_id = inv_product_ids and inv_product_ids[0]
                    
                    if not split_product_id:
                        raise ValidationError(_('No Split Product is passed/invoice do not have any lines with product.'))
                    
                    new_inv_id.invoice_line_ids.with_context(check_move_validity=False).unlink()
                    self.split_record_full_inv_new_line_section(new_inv_id)
                    self.acs_create_new_invoice_line(new_inv_id, split_product_id, amount)

                    self.split_record_full_inv_new_line_section(active_record)
                    self.acs_create_new_invoice_line(active_record, split_product_id, -amount)
                    
                    
            if self.split_selection == 'lines':
                for line in self.line_ids:
                    price_to_split = 0
                    if self.line_split_selection == 'price':
                        price_to_split = line.price_to_split
                    elif self.line_split_selection == 'percentage':
                        price_to_split = line.line_id.price_unit * (line.percentage_to_split / 100)

                    line.line_id.with_context(check_move_validity=False).write({
                        'qty_to_split': line.qty_to_split,
                        'price_to_split': price_to_split,
                        'full_cover': line.full_cover,
                    })

                if self.line_split_selection == 'qty':
                    new_inv_id = self.split_lines(active_record, 'qty_to_split', 'quantity')

                if self.line_split_selection in ['price', 'percentage']:
                    new_inv_id = self.split_lines(active_record, 'price_to_split', 'price_unit')

            
            #incase of split if want to keep add data in new inv and one line in old invoice
            if self.update_partner:
                current_new_invoice = new_inv_id
                old_partner = active_record.partner_id
                active_record.partner_id = self.partner_id.id
                new_inv_id.partner_id = old_partner.id
                #Return current invoice as insurance invoice.
                new_inv_id = active_record
                active_record = current_new_invoice

            new_inv_id.with_context(check_move_validity=False)._onchange_partner_id()
        
            new_inv_id.message_post_with_source('mail.message_origin_link',
                render_values={'self': new_inv_id, 'origin': active_record},
                subtype_id=self.env.ref('mail.mt_note').id
            )
            active_record.message_post_with_source('mail.message_origin_link',
                render_values={'self': active_record, 'origin': new_inv_id, 'edit': True,},
                subtype_id=self.env.ref('mail.mt_note').id
            )
        return new_inv_id, active_record
