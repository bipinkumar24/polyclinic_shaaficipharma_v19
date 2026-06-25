# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockReportWizard(models.TransientModel):
    _name = 'pharmacy.stock.report.wizard'
    _description = 'Pharmacy Stock Report Wizard'

    report_type = fields.Selection(
        selection=[
            ('position', 'Current Stock Position'),
            ('valuation', 'Stock Valuation'),
            ('movement', 'Fast / Slow / Dead Stock'),
            ('reorder', 'Reorder Level'),
            ('batch', 'Batch / Lot Tracking'),
        ], string='Report Type', default='position', required=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category')
    movement_class = fields.Selection(
        selection=[
            ('fast', 'Fast Moving'),
            ('slow', 'Slow Moving'),
            ('dead', 'Dead Stock'),
        ], string='Movement Class')

    def action_view_report(self):
        """Open the selected stock report."""
        self.ensure_one()
        mapping = {
            'position': ('report.pharmacy.stock.position',
                         _('Stock Position'), 'list,pivot'),
            'valuation': ('report.pharmacy.stock.valuation',
                          _('Stock Valuation'), 'list,pivot,graph'),
            'movement': ('report.pharmacy.stock.movement',
                         _('Stock Movement'), 'list,pivot'),
            'reorder': ('report.pharmacy.reorder',
                        _('Reorder Level'), 'list'),
            'batch': ('report.pharmacy.batch.tracking',
                      _('Batch Tracking'), 'list'),
        }
        model, name, views = mapping[self.report_type]
        domain = []
        if self.pharmacy_category_id and self.report_type in (
                'position', 'valuation', 'movement', 'reorder'):
            domain.append(('pharmacy_category_id', '=', self.pharmacy_category_id.id))
        if self.movement_class and self.report_type == 'movement':
            domain.append(('movement_class', '=', self.movement_class))
        if self.report_type == 'reorder':
            domain.append(('needs_reorder', '=', True))
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': model,
            'view_mode': views,
            'domain': domain,
        }

    def action_refresh_movement(self):
        """Trigger an on-demand refresh of the movement analysis."""
        self.env['report.pharmacy.stock.movement'].sudo().refresh_movement_analysis()
        return self.action_view_report()
