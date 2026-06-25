# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DirectPrintLabelWizard(models.TransientModel):
    _name = 'odoo.leeno.direct.print.label.wizard'
    _description = 'Print Labels Wizard'

    print_format = fields.Selection([
        ('dymo', 'Dymo'),
        ('2x7xprice', '2 x 7 with price'),
        ('4x7xprice', '4 x 7 with price'),
        ('4x12', '4 x 12'),
        ('4x12xprice', '4 x 12 with price'),
    ], string="Label Format", default='2x7xprice', required=True)

    quantity = fields.Integer(
        string='Number of Labels',
        default=1,
        required=True,
        help='Number of label copies to print per product.',
    )

    product_ids = fields.Many2many(
        'product.product',
        'leeno_direct_print_label_wiz_product_rel',
        string='Products',
    )
    product_tmpl_ids = fields.Many2many(
        'product.template',
        'leeno_direct_print_label_wiz_tmpl_rel',
        string='Product Templates',
    )

    model = fields.Char(string='Source Model')
    res_ids_json = fields.Char(string='Record IDs')
    product_count = fields.Integer(
        string='Products Selected',
        compute='_compute_product_count',
    )

    @api.depends('product_ids', 'product_tmpl_ids')
    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_ids) or len(rec.product_tmpl_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self._context

        model = ctx.get('default_model') or ctx.get('active_model', '')
        active_ids = ctx.get('default_res_ids') or ctx.get('active_ids', [])
        if not active_ids and ctx.get('active_id'):
            active_ids = [ctx['active_id']]

        res['model'] = model
        res['res_ids_json'] = json.dumps(active_ids)

        # Resolve products from the source model
        if model == 'product.product' and active_ids:
            res['product_ids'] = [(6, 0, active_ids)]
        elif model == 'product.template' and active_ids:
            res['product_tmpl_ids'] = [(6, 0, active_ids)]
        elif model == 'stock.picking' and active_ids:
            pickings = self.env['stock.picking'].browse(active_ids)
            product_ids = pickings.mapped('move_ids.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]
        elif model == 'sale.order' and active_ids:
            orders = self.env['sale.order'].browse(active_ids)
            product_ids = orders.mapped('order_line.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]
        elif model == 'purchase.order' and active_ids:
            orders = self.env['purchase.order'].browse(active_ids)
            product_ids = orders.mapped('order_line.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]
        elif model == 'account.move' and active_ids:
            moves = self.env['account.move'].browse(active_ids)
            product_ids = moves.mapped('invoice_line_ids.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]
        elif model == 'prescription.order' and active_ids:
            prescription = self.env['prescription.order'].browse(active_ids)
            product_ids = prescription.mapped('prescription_line_ids.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]
        elif model == 'acs.radiology.request' and active_ids:
            radiology =  self.env['acs.radiology.request'].browse(active_ids)
            product_ids = radiology.mapped('line_ids.test_id.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]
        elif model == 'acs.laboratory.request' and active_ids:
            laboratory =  self.env['acs.laboratory.request'].browse(active_ids)
            product_ids = laboratory.mapped('line_ids.test_id.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]

        elif model == 'hms.appointment' and active_ids:
            appointment =  self.env['hms.appointment'].browse(active_ids)
            product_ids = appointment.mapped('patient_procedure_ids.product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]

        return res

    def _get_report_xml_id(self):
        """Return the XML ID of the label report matching the chosen format."""
        fmt = self.print_format
        if fmt == 'dymo':
            return 'product.report_product_template_label_dymo'
        if 'x' in fmt:
            parts = fmt.split('x')[:2]
            cols = parts[0] if parts[0].isdigit() else '4'
            rows = parts[1] if parts[1].isdigit() else '12'
            xml_id = 'product.report_product_template_label_%sx%s' % (cols, rows)

            if 'xprice' not in fmt:
                xml_id += '_noprice'

            return xml_id
        return ''

    def _create_label_layout(self):
        """Create a product.label.layout wizard record matching our settings,
        so that the standard Odoo label reports can look up pricelist / format
        from it."""
        vals = {
            'print_format': self.print_format,
            'custom_quantity': self.quantity,
        }
        if self.product_tmpl_ids:
            vals['product_tmpl_ids'] = [(6, 0, self.product_tmpl_ids.ids)]
        elif self.product_ids:
            vals['product_ids'] = [(6, 0, self.product_ids.ids)]
        return self.env['product.label.layout'].create(vals)

    def action_print_labels(self):
        """Generate the label PDF and open the browser print dialog."""
        self.ensure_one()

        if self.quantity <= 0:
            raise UserError(_('Please enter a positive number of labels.'))

        # Determine products
        if self.product_tmpl_ids:
            products = self.product_tmpl_ids.ids
            active_model = 'product.template'
        elif self.product_ids:
            products = self.product_ids.ids
            active_model = 'product.product'
        else:
            raise UserError(_('No products selected for label printing.'))

        xml_id = self._get_report_xml_id()

        if not xml_id:
            raise UserError(_('Unable to determine the label report for format "%s".', self.print_format))

        report = self.env.ref(xml_id, raise_if_not_found=False)

        if not report:
            raise UserError(_('Label report "%s" not found. Make sure the product module is installed.', xml_id))

        # Create a real product.label.layout record so the report can look it up
        layout = self._create_label_layout()

        data = {
            'active_model': active_model,
            'quantity_by_product': {p: self.quantity for p in products},
            'layout_wizard': layout.id,
            'price_included': 'xprice' in self.print_format,
            'widget': 'monetary',
        }
        report_name = report.report_name
        report_action = report.report_action(None, data=data, config=False)
        if report_action.get('type') == 'ir.actions.report':
            return {
                'type': 'ir.actions.client',
                'tag': 'leeno_direct_print_label_browser',
                'params': {
                    'report_name': report_name,
                    'data': data,
                    'xml_id': xml_id,
                    'title': 'Product Labels',
                },
            }
      
        return report_action

    def action_download_labels(self):
        """Standard download (non-direct-print) fallback."""
        self.ensure_one()

        if self.quantity <= 0:
            raise UserError(_('Please enter a positive number of labels.'))

        if self.product_tmpl_ids:
            products = self.product_tmpl_ids.ids
            active_model = 'product.template'
        elif self.product_ids:
            products = self.product_ids.ids
            active_model = 'product.product'
        else:
            raise UserError(_('No products selected for label printing.'))

        xml_id = self._get_report_xml_id()

        if not xml_id:
            raise UserError(_('Unable to determine the label report for format "%s".', self.print_format))

        report = self.env.ref(xml_id, raise_if_not_found=False)
        if not report:
            raise UserError(_('Label report "%s" not found.', xml_id))

        # Create a real product.label.layout record so the report can look it up
        layout = self._create_label_layout()

        data = {
            'active_model': active_model,
            'quantity_by_product': {p: self.quantity for p in products},
            'layout_wizard': layout.id,
            'price_included': 'xprice' in self.print_format,
        }
        report_action = report.report_action(None, data=data, config=False)
        report_action.update({'close_on_report_download': True})
        return report_action
