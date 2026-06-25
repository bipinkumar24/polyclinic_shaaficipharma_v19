# -*- coding: utf-8 -*-
import base64
import io
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SalesReportWizard(models.TransientModel):
    _name = 'pharmacy.sales.report.wizard'
    _description = 'Pharmacy Sales Report Wizard'

    date_from = fields.Date(
        string='Date From', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(
        string='Date To', required=True,
        default=fields.Date.context_today)
    branch_ids = fields.Many2many('pharmacy.branch', string='Branches')
    cashier_ids = fields.Many2many('res.users', string='Cashiers')
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category')
    group_by = fields.Selection(
        selection=[
            ('day', 'Daily'),
            ('week', 'Weekly'),
            ('month', 'Monthly'),
        ], string='Period', default='day', required=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wiz in self:
            if wiz.date_from > wiz.date_to:
                raise UserError(_('Date From must precede Date To.'))

    def _build_domain(self):
        domain = [
            ('order_date', '>=', self.date_from),
            ('order_date', '<=', self.date_to),
            ('state', 'in', ('paid', 'done', 'invoiced')),
        ]
        if self.branch_ids:
            domain.append(('branch_id', 'in', self.branch_ids.ids))
        if self.cashier_ids:
            domain.append(('cashier_id', 'in', self.cashier_ids.ids))
        if self.pharmacy_category_id:
            domain.append(('pharmacy_category_id', '=', self.pharmacy_category_id.id))
        return domain

    def action_view_report(self):
        """Open the sales report list/pivot filtered by wizard criteria."""
        self.ensure_one()
        return {
            'name': _('POS Sales Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'report.pharmacy.sales',
            'view_mode': 'list,pivot,graph',
            'domain': self._build_domain(),
            'context': {'search_default_group_branch': 1},
        }

    def action_export_xlsx(self):
        """Export the filtered sales report to an XLSX file."""
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_(
                'The xlsxwriter Python library is required for Excel '
                'export. Please install it on the server.'))

        records = self.env['report.pharmacy.sales'].search(
            self._build_domain())
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(_('POS Sales'))

        bold = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2'})
        money = workbook.add_format({'num_format': '#,##0.00'})

        headers = [_('Date'), _('Branch'), _('Cashier'), _('Product'),
                   _('Category'), _('Qty'), _('Net Sales'),
                   _('Gross Sales'), _('Taxes'), _('Discounts'),
                   _('Margin')]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, bold)

        row = 1
        for rec in records:
            sheet.write(row, 0, str(rec.order_date or ''))
            sheet.write(row, 1, rec.branch_id.name or '')
            sheet.write(row, 2, rec.cashier_id.name or '')
            sheet.write(row, 3, rec.product_id.display_name or '')
            sheet.write(row, 4, rec.pharmacy_category_id.name or '')
            sheet.write(row, 5, rec.qty)
            sheet.write(row, 6, rec.price_subtotal, money)
            sheet.write(row, 7, rec.price_total, money)
            sheet.write(row, 8, rec.tax_amount, money)
            sheet.write(row, 9, rec.discount_amount, money)
            sheet.write(row, 10, rec.margin, money)
            row += 1

        sheet.set_column(0, 0, 18)
        sheet.set_column(1, 4, 22)
        sheet.set_column(5, 10, 14)
        workbook.close()
        output.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': 'pharmacy_sales_report.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.'
                        'spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
