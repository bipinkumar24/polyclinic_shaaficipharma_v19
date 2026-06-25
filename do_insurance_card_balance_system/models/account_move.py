from odoo import api, fields, models, _
from odoo.exceptions import UserError

class Invoice(models.Model):
    _inherit = 'account.move'

    def acs_create_insurance_card_invoice(self, **data):
        card_insurance_company_id = data.get('card_insurance_company_id')
        available_insurancecard_balance = data.get('available_insurancecard_balance')
        patient_amount = data.get('patient_amount')
        acs_object = data.get('acs_object')
        inv_type = data.get('inv_type')
        insurance_amount = data.get('insurance_amount')
        rec_field = data.get('rec_field')
        line_ids = data.get('line_ids')
        insurance_invoice_id = False
        #Check if copayment amount is 25 and invoice amount is 25 no need to bill.
        if card_insurance_company_id:

            patient_amount = patient_amount
            wizard_lines = []
            if line_ids:
                for line in line_ids:
                    wizard_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                    }))
            split_context = {
                'active_model':'account.move', 
                'active_id': self.id,
                'available_insurancecard_balance': available_insurancecard_balance,
                'insurance_amount': patient_amount,
                'partner_id': card_insurance_company_id.id if card_insurance_company_id else self.partner_id.id,
            }

            wiz_id = self.env['split.invoice.wizard'].with_context(split_context).create({
                'split_selection': 'invoice',
                'fixamount': patient_amount,
                'partner_id': card_insurance_company_id.id if card_insurance_company_id else self.partner_id.id,
            })
            insurance_invoice_id, inv_id = wiz_id.split_record()
            insurance_invoice_id.write({
                rec_field: acs_object.id,
                'ref': acs_object.name,
                # 'invoice_split_by': 'fixamount',
                'invoice_origin': acs_object.name,
                'hospital_invoice_type': inv_type,
                'patient_invoice_id': self.id,
            })
            if line_ids:
                wizard_lines.append((0,0,{
                    'display_type':'line_section',
                    'name':'Insurance Share'
                }))

                wizard_lines.append((0,0,{
                    'name':'Insurance Adjustment',
                    'quantity':1,
                    'price_unit':-insurance_amount
                }))

                inv_id.write({
                    'invoice_line_ids': [(5,0,0)] + wizard_lines
                })

        return insurance_invoice_id

    def update_commission_values_action(self):
        Commission = self.env['acs.commission']
        for rec in self:
             rec.update_commission_values()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def acs_get_line_patient_share_card_amount(self, insurance, for_split=False):
        amount = 0
        Rule = self.env['acs.insurance.policy.rule']
        matching_rule = False
        product_tmpl_id = self.product_id.product_tmpl_id.id
        product_categ_id = self.product_id.categ_id.id
        excluded_product_ids = insurance.acs_get_excluded_product_ids()

        if insurance.policy_rule_ids:
            rule_ids = insurance.policy_rule_ids.ids
            matching_rule = Rule.search([('id','in',rule_ids),
                ('product_id','=',product_tmpl_id)], limit=1)
            if not matching_rule:
                matching_rule = Rule.search([('id','in',rule_ids),
                ('product_category_id','=',product_categ_id)], limit=1)

        if not matching_rule and insurance.insurance_company_id.policy_rule_ids:
            company_rule_ids = insurance.insurance_company_id.policy_rule_ids.ids
            matching_rule = Rule.search([('id','in', company_rule_ids),
                ('product_id','=',product_tmpl_id)], limit=1)
            if not matching_rule:
                matching_rule = Rule.search([('id','in', company_rule_ids),
                ('product_category_id','=',product_categ_id)], limit=1)

        if matching_rule and self.product_id.id not in excluded_product_ids:
            if matching_rule.rule_type == 'percentage':
                price = self.price_subtotal
                if for_split:
                    price = self.price_unit
                    if matching_rule.full_cover:
                        price = -1 * price
                amount = (matching_rule.percentage * price)/100
                
            elif matching_rule.rule_type == 'amount':
                amount = matching_rule.amount
        return amount