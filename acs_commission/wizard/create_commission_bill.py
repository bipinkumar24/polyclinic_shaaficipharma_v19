# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ACSCommissionBill(models.TransientModel):
    _name = "commission.bill"
    _description = "Create Commission Bill"

    @api.model
    def _get_default_journal(self):
        journal_domain = [
            ('type', '=', 'purchase'),
            ('company_id', '=', self.env.company.id),
        ]
        default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
        return default_journal_id.id and default_journal_id or False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('multiple'):
            active_ids = self.env.context.get('active_ids')

            if not active_ids:
                raise UserError("No commission sheets selected.")

            res['commission_sheet_ids'] = [(6, 0, active_ids)]
        return res

    commission_sheet_ids = fields.Many2many(
        'acs.commission.sheet',
        string='Commission Sheets',
        readonly=True
    )
    hide_groupby_partner = fields.Boolean(string='Hide Group by Partner')
    groupby_partner = fields.Boolean(string='Group by Partner',
        help='Set true if want to create single bill for Partner')
    print_commission = fields.Boolean(string='Add Commission no in Description',
        help='Set true if want to append SO in bill line Description', default=True)
    journal_id = fields.Many2one('account.journal', default=_get_default_journal, required=True)

    def create_bill(self, line):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'ref': False,
            'partner_id': line.partner_id.id,
            'journal_id': self.journal_id.id
        }) 
        return bill

    def create_bill_line(self, line, bill, product_id, print_commission=False, amount=None, custom_name=None):
        account_id = product_id.property_account_income_id or product_id.categ_id.property_account_income_categ_id
        if not account_id:
            raise UserError(
                _('There is no income account defined for this product: "%s".') % (product_id.name,)
            )

        if custom_name:
            name = custom_name
        else:
            name = product_id.name
            if print_commission:
                name = name + ': ' + line.name

        price = amount if amount is not None else line.payable_amount

        inv_line = self.env['account.move.line'].with_context(check_move_validity=False).create({
            'move_id': bill.id,
            'name': name,
            'price_unit': price,
            'quantity': 1,
            'discount': 0.0,
            'product_uom_id': product_id.uom_id.id,
            'product_id': product_id.id,
            'account_id': account_id.id,
            'tax_ids': [(6, 0, product_id.supplier_taxes_id.ids)],
            'display_type': 'product',
        })
        return inv_line

    def create_bills(self):
        Commission = self.env['acs.commission']
        bills = []
        product_id = self.env.company.commission_product_id

        if self.commission_sheet_ids:
            lines = self.commission_sheet_ids.commission_line_ids

            for sheet in self.commission_sheet_ids:
                if sheet.payment_invoice_id:
                    raise UserError(_('Already Bill is created for %s') % sheet.name)
        else:
            lines = Commission.browse(self.env.context.get('active_ids', []))

        if not lines:
            raise UserError(_('No commission lines found.'))

        if any(line.target_based_commission and not line.commission_sheet_id for line in lines):
            raise UserError(_('Commission Bill can be created from commission sheet only for target based commissions.'))

        if not product_id:
            raise UserError(_('Please set Commission Product in company first.'))

        partners = lines.mapped('partner_id')
        if len(partners) > 1:
            raise UserError(_('You cannot create a vendor bill for multiple vendors. Please select records with the same vendor.'))

        # partner = partners[0]

        lines = lines.filtered(lambda l: not l.invoice_line_id)
        if not lines:
            raise UserError(_('Nothing to bill. All commissions are already billed.'))

        total_amount = sum(lines.mapped('payable_amount'))

        bill = self.create_bill(lines[0])

        if self.print_commission:
            names = ', '.join(lines.mapped('name'))
            line_name = f"{product_id.name}: {names}"
        else:
            line_name = product_id.name

        inv_line = self.create_bill_line(
            line=lines[0],  # dummy reference
            bill=bill,
            product_id=product_id,
            print_commission=False,  # already handled
            amount=total_amount,
            custom_name=line_name
        )

        for line in lines:
            line.invoice_line_id = inv_line.id

        bills.append(bill.id)

        if self.commission_sheet_ids:
            for sheet in self.commission_sheet_ids:
                sheet.payment_invoice_id = bill.id

        if self.env.context.get('open_bills', False):
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = bill.id
            return action

        return {'type': 'ir.actions.act_window_close'}
