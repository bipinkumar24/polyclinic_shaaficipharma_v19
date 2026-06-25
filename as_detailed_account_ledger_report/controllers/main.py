import io
import json
import base64
import xlsxwriter
from odoo import http
from odoo.http import request, content_disposition


class XLSXReportController(http.Controller):

    @http.route('/reports/xlsx/account_ledger', type='http', auth="user", methods=['GET'])
    def get_account_ledger_xlsx(self, data, **kw):
        data = json.loads(data.replace("'", "\""))
        wizard = request.env['account.ledger.wizard'].browse(data['wizard_id'])

        report_data = request.env['report.as_detailed_account_ledger_report.report_ledger_template']._get_report_values(
            [wizard.id])
        company = request.env.user.company_id

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Account Ledger')

        # Custom number format for accounting style
        accounting_format_string = '#,##0.00;(#,##0.00)'

        # ==========================================================
        # FONT FIX: All formats now include 'font_name': 'Ubuntu'
        # ==========================================================

        # 1. Create a default format for all standard cells
        default_format = workbook.add_format({'font_name': 'Ubuntu'})

        # 2. Ensure all other formats also have the font name
        company_format = workbook.add_format(
            {'bold': True, 'font_size': 12, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Ubuntu'})
        title_format = workbook.add_format(
            {'bold': True, 'font_size': 20, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Ubuntu'})
        subtitle_format = workbook.add_format(
            {'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Ubuntu'})
        bold_format = workbook.add_format({'bold': True, 'font_name': 'Ubuntu'})
        money_format = workbook.add_format({'num_format': accounting_format_string, 'font_name': 'Ubuntu'})
        header_format = workbook.add_format(
            {'bold': True, 'bg_color': '#B2E2E2', 'border': 1, 'font_name': 'Ubuntu', 'align': 'center',
             'valign': 'vcenter'})
        subtotal_format = workbook.add_format(
            {'bold': True, 'bg_color': '#FAF0E6', 'num_format': accounting_format_string, 'font_name': 'Ubuntu',
             'top': 1, 'bottom': 1})
        total_format = workbook.add_format(
            {'bold': True, 'bg_color': '#D2B4B4', 'num_format': accounting_format_string, 'font_name': 'Ubuntu',
             'top': 1, 'bottom': 1})
        date_left_format = workbook.add_format({'bold': True, 'font_name': 'Ubuntu', 'align': 'left'})
        date_right_format = workbook.add_format({'bold': True, 'font_name': 'Ubuntu', 'align': 'right'})
        subtotal_date_format = workbook.add_format(
            {'bold': True, 'bg_color': '#FAF0E6', 'top': 1, 'bottom': 1, 'font_name': 'Ubuntu'})
        subtotal_blank_format = workbook.add_format({'bg_color': '#FAF0E6', 'top': 1, 'bottom': 1})
        total_label_format = workbook.add_format(
            {'bold': True, 'bg_color': '#D2B4B4', 'align': 'right', 'top': 1, 'bottom': 1, 'font_name': 'Ubuntu'})
        total_blank_format = workbook.add_format({'bg_color': '#D2B4B4', 'top': 1, 'bottom': 1})

        # Column Widths
        sheet.set_column('A:A', 12);
        sheet.set_column('B:B', 25);
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 30);
        sheet.set_column('E:E', 10);
        sheet.set_column('F:F', 22)
        sheet.set_column('G:G', 10);
        sheet.set_column('H:H', 12);
        sheet.set_column('I:I', 15)
        sheet.set_column('J:J', 15);
        sheet.set_column('K:K', 15)

        # Company Name Header
        sheet.merge_range('A1:K1', company.name, company_format)

        # Main report titles
        sheet.merge_range('A2:K2', 'Account Ledger', title_format)
        sheet.merge_range('A3:K3', f"Account Head: {report_data['account'].code} - {report_data['account'].name}",
                          subtitle_format)

        sheet.merge_range('A5:F5', f"Date From: {report_data['date_from']}   To: {report_data['date_to']}",
                          date_left_format)
        sheet.merge_range('G5:K5', f"Date Printed: {report_data['date_printed']}", date_right_format)

        # Opening and Closing Balances
        sheet.write('A7', 'Opening:', bold_format)
        sheet.write('B7', report_data['opening_balance'], money_format)
        sheet.write('J7', 'Closing:', date_right_format)
        sheet.write('K7', report_data['closing_balance'], money_format)

        # Table Headers
        col_headers = ['Date', 'Business Partner', 'Product', 'Reference', 'Type', 'Document No', 'Quantity', 'Rate',
                       'Debit Value', 'Credit Value', 'Doc Status']
        sheet.write_row('A9', col_headers, header_format)

        # Write Data Rows
        row = 9
        grand_total_debit = 0
        grand_total_credit = 0
        for report_date in report_data['sorted_dates']:
            daily_subtotal_debit = 0
            daily_subtotal_credit = 0
            for line in report_data['lines_by_date'][report_date]:
                # 3. Apply the default_format to all non-numeric cells
                sheet.write(row, 0, line.date.strftime('%d/%m/%Y'), default_format)
                sheet.write(row, 1, line.partner_id.name or '', default_format)
                sheet.write(row, 2, line.product_id.name or '', default_format)
                sheet.write(row, 3, line.name or '', default_format)
                sheet.write(row, 4, line.journal_id.type or '', default_format)
                sheet.write(row, 5, line.move_id.name or '', default_format)
                sheet.write(row, 6, line.quantity, default_format)  # Quantity can be default or a number format
                #sheet.write(row, 7, line.price_unit, money_format)
                rate_to_write = line.price_unit
                if line.price_unit == 0 and line.quantity != 0:
                    if line.debit != 0:
                        rate_to_write = line.debit / line.quantity
                    elif line.credit != 0:
                        rate_to_write = line.credit / line.quantity
                sheet.write(row, 7, rate_to_write, money_format)
                #
                sheet.write(row, 8, line.debit, money_format)
                sheet.write(row, 9, line.credit, money_format)
                sheet.write(row, 10, report_data['get_status_label'](line.move_id.state), default_format)
                daily_subtotal_debit += line.debit
                daily_subtotal_credit += line.credit
                row += 1

            sheet.merge_range(row, 0, row, 7, report_date.strftime('%d-%b-%y'), subtotal_date_format)
            sheet.write(row, 8, daily_subtotal_debit, subtotal_format)
            sheet.write(row, 9, daily_subtotal_credit, subtotal_format)
            sheet.write(row, 10, '', subtotal_blank_format)
            grand_total_debit += daily_subtotal_debit
            grand_total_credit += daily_subtotal_credit
            row += 1

        sheet.merge_range(row, 0, row, 7, 'Total', total_label_format)
        sheet.write(row, 8, grand_total_debit, total_format)
        sheet.write(row, 9, grand_total_credit, total_format)
        sheet.write(row, 10, '', total_blank_format)

        workbook.close()
        output.seek(0)

        return request.make_response(
            output.read(),
            [
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(f"{report_data['account'].code}_Ledger.xlsx"))
            ]
        )