# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SplitInvoiceWizard(models.TransientModel):
    _inherit = 'split.invoice.wizard'

    def split_lines(self, active_record, split_field, update_field):
        res = super().split_lines(active_record, split_field, update_field)
        insurance_id = self.env.context.get('insurance_id')
        insurance_type = self.env.context.get('insurance_type')
        insurance_id = self.env['hms.patient.insurance'].browse(insurance_id)
        if insurance_id and insurance_type=='fix':
            active_record.invoice_line_ids.write({
                'discount': 0
            })
        return res

    @api.model_create_multi
    def create(self, vals_list):
        insurance_id = self.env.context.get('insurance_id')
        insurance_type = self.env.context.get('insurance_type')
        insurance_amount = self.env.context.get('insurance_amount')
        insurance_percentage = self.env.context.get('insurance_percentage')
        available_insurancecard_balance = self.env.context.get('available_insurancecard_balance')
        partner_id = self.env.context.get('partner_id')
        values = {}

        if insurance_id or available_insurancecard_balance:
            insurance_id = self.env['hms.patient.insurance'].browse(insurance_id)
            active_record = self.env['account.move'].browse(self.env.context.get('active_id'))
            split_product_id = insurance_id.insurance_company_id.patient_share_product_id and insurance_id.insurance_company_id.patient_share_product_id.id or False
            if insurance_id.patient_share_by_rule:
                for values in vals_list:
                    lines = []
                    for line in active_record.invoice_line_ids.filtered(lambda x: x.display_type=='product'):
                        price_unit = line.acs_get_line_patient_share_amount(insurance_id, for_split=True)
                        if price_unit:
                            lines.append((0,0,{
                                'name': line.name,
                                'product_id': line.product_id and line.product_id.id or False,
                                'line_id': line.id,
                                'quantity': line.quantity,
                                'price': line.price_unit,
                                'price_to_split': price_unit,
                                'display_type': line.display_type,
                                'full_cover': True if price_unit < 0 else False,
                            }))
                    values.update({
                        'split_selection': 'lines', 
                        'line_split_selection': 'price', 
                        'line_ids': lines,
                        'partner_id': insurance_id.insurance_company_id.partner_id.id if insurance_id.insurance_company_id.partner_id else self.partner_id.id,
                        'split_product_id': split_product_id,
                        'update_partner': True
                    })

            elif insurance_type=='fix':
                if insurance_id.patient_share_in_invoice:
                    for values in vals_list:
                        values.update({
                            'split_selection': 'invoice', 
                            'invoice_split_type': 'new_line', 
                            'invoice_split_by': 'fixamount',
                            'partner_id': insurance_id.insurance_company_id.partner_id.id if insurance_id.insurance_company_id.partner_id else self.partner_id.id,
                            'fixamount': insurance_amount,
                            'split_product_id': split_product_id,
                            'update_partner': True
                        })

                else: 
                    for values in vals_list:
                        lines = []
                        app_insurance_amount = insurance_amount
                        rem_insurance_amount = insurance_amount
                        invoice_line = active_record.invoice_line_ids[0]
                        for line in active_record.invoice_line_ids:
                            if app_insurance_amount and rem_insurance_amount:
                                if rem_insurance_amount<=line.price_unit:
                                    price_unit = line.price_unit - rem_insurance_amount
                                    rem_insurance_amount = 0
                                else:
                                    price_unit = line.price_unit
                                    rem_insurance_amount -= price_unit
                            else:
                                price_unit = line.price_unit

                            lines.append((0,0,{
                                'name': line.name,
                                'product_id': line.product_id and line.product_id.id or False,
                                'line_id': line.id,
                                'quantity': line.quantity,
                                'price': line.price_unit,
                                'qty_to_split': 1,
                                'price_to_split': price_unit,
                                'display_type': line.display_type,
                            }))
                        values.update({
                            'split_selection': 'lines', 
                            'line_split_selection': 'price', 
                            'line_ids': lines,
                            'partner_id': insurance_id.insurance_company_id.partner_id.id if insurance_id.insurance_company_id.partner_id else self.partner_id.id,
                            'split_product_id': split_product_id,
                        })
            elif insurance_type=='percentage_with_max':
                for values in vals_list:
                    lines = []
                    app_insurance_amount = insurance_amount
                    rem_insurance_amount = insurance_amount
                    for line in active_record.invoice_line_ids:
                        line_price = (line.price_unit * insurance_percentage)/100
                        #if line amount is greater than remaining amount use remaining amount only
                        if line_price > rem_insurance_amount:
                            line_price = rem_insurance_amount
                        if app_insurance_amount and rem_insurance_amount:
                            if rem_insurance_amount<=line_price:
                                rem_insurance_amount = 0
                            else:
                                rem_insurance_amount -= line_price

                        lines.append((0,0,{
                            'name': line.name,
                            'product_id': line.product_id and line.product_id.id or False,
                            'line_id': line.id,
                            'quantity': line.quantity,
                            'price': line.price_unit,
                            'qty_to_split': 1,
                            'price_to_split': line_price,
                            'display_type': line.display_type,
                        }))
                    values.update({
                        'split_selection': 'lines', 
                        'line_split_selection': 'price', 
                        'line_ids': lines,
                        'partner_id': insurance_id.insurance_company_id.partner_id.id if insurance_id.insurance_company_id.partner_id else self.partner_id.id,
                        'split_product_id': split_product_id,
                    })
            elif available_insurancecard_balance:
                for values in vals_list:
                    values.update({
                        'split_selection': 'invoice', 
                        'invoice_split_type': 'new_line', 
                        'invoice_split_by': 'fixamount',
                        'partner_id': partner_id,
                        'fixamount': insurance_amount,
                        'update_partner': True
                    })
            else:
                #incase of 100% insurance to show proper product we need to pass it
                for values in vals_list:
                    values['split_product_id'] = split_product_id
        return super().create(vals_list)

    #Update label as Patient Share
    def split_record_full_inv_new_line_section(self, invoice):
        self.env['account.move.line'].with_context(check_move_validity=False).create({
            'move_id': invoice.id,
            'name': _("Patient Share"),
            'display_type': 'line_section',
        })

    #Add patient share 0 also with new section of patient share is true on insurance.
    def split_record(self):
        insurance_invoice_id, inv_id = super().split_record()
        insurance_id = self.env.context.get('insurance_id')
        insurance_type = self.env.context.get('insurance_type')
        available_insurancecard_balance = self.env.context.get('available_insurancecard_balance')
        if insurance_id:
            insurance_id = self.env['hms.patient.insurance'].browse(insurance_id)
            excluded_product_ids = insurance_id.acs_get_excluded_product_ids()
            if insurance_type=='fix' or self.percentage==100:
                if insurance_id.patient_share_in_invoice and (self.fixamount==0 or self.percentage==100):
                    self.split_record_full_inv_new_line_section(insurance_invoice_id)
                    split_product_id = self.split_product_id
                    if not split_product_id:
                        inv_product_ids = insurance_invoice_id.invoice_line_ids.mapped('product_id')
                        split_product_id = inv_product_ids and inv_product_ids[0]
                    self.acs_create_new_invoice_line(insurance_invoice_id, split_product_id, 0)

            #Move excluded lines to new invoice
            if excluded_product_ids:
                lines_to_remove = []
                for line in insurance_invoice_id.invoice_line_ids:
                    #Writing move_id directly to line causes amount total issue.
                    #So creating new line with move_id and unlinking old line
                    if line.product_id.id in excluded_product_ids:
                        line.create({
                            'move_id': inv_id.id,
                            'name': line.name,
                            'product_id': line.product_id and line.product_id.id or False,
                            'quantity': line.quantity,
                            'price_unit': line.price_unit,
                            'discount': line.discount,
                            'display_type': line.display_type,
                            'product_uom_id': line.product_uom_id.id,
                            'tax_ids': line.tax_ids.ids,
                        })
                        lines_to_remove.append(line)
                for line in lines_to_remove:
                    line.unlink()
        elif available_insurancecard_balance:
            if self.split_product_id:
                self.split_record_full_inv_new_line_section(insurance_invoice_id)
                split_product_id = self.split_product_id

        return insurance_invoice_id, inv_id
