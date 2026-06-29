# -*- coding: utf-8 -*-
import os

from odoo import http, fields
from odoo.http import request


class GrnScanner(http.Controller):

    # ------------------------------------------------------------------
    # Page
    # ------------------------------------------------------------------
    @http.route('/grn/scanner', type='http', auth='user')
    def scanner_page(self, **kw):
        module_dir = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(module_dir, 'static', 'src', 'scanner.html')
        with open(path, 'r', encoding='utf-8') as fh:
            html = fh.read()
        return request.make_response(
            html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    # ------------------------------------------------------------------
    # Data: pending incoming receipts
    # ------------------------------------------------------------------
    @http.route('/grn/scanner/pickings', type='jsonrpc', auth='user')
    def pickings(self, **kw):
        Picking = request.env['stock.picking']
        domain = [
            ('picking_type_code', '=', 'incoming'),
            ('state', 'in', ('assigned', 'confirmed')),
            ('company_id', 'in', request.env.companies.ids),
        ]
        recs = Picking.search(domain, limit=100, order='scheduled_date desc')
        return [{
            'id': p.id,
            'name': p.name,
            'partner': p.partner_id.display_name or '',
            'origin': p.origin or '',
            'scheduled_date': fields.Datetime.to_string(p.scheduled_date) or '',
            'state': p.state,
            'line_count': len(p.move_ids),
        } for p in recs]

    # ------------------------------------------------------------------
    # Data: lines of one receipt
    # ------------------------------------------------------------------
    @http.route('/grn/scanner/picking/<int:picking_id>', type='jsonrpc', auth='user')
    def picking_lines(self, picking_id, **kw):
        p = request.env['stock.picking'].browse(picking_id)
        if not p.exists() or p.picking_type_code != 'incoming':
            return {'error': 'Receipt not found.'}
        lines = []
        for m in p.move_ids:
            prod = m.product_id
            lines.append({
                'move_id': m.id,
                'product_id': prod.id,
                'name': prod.display_name,
                'barcode': prod.barcode or '',
                'default_code': prod.default_code or '',
                'demand': m.product_uom_qty,
                'done': m.quantity,
                'tracking': prod.tracking,
                'use_expiration': prod.use_expiration_date,
                'uom': m.product_uom.name,
            })
        return {'id': p.id, 'name': p.name, 'state': p.state, 'lines': lines}

    # ------------------------------------------------------------------
    # Submit scanned lines
    # ------------------------------------------------------------------
    @http.route('/grn/scanner/submit', type='jsonrpc', auth='user')
    def submit(self, picking_id=None, lines=None, **kw):
        lines = lines or []
        p = request.env['stock.picking'].browse(int(picking_id or 0))
        if not p.exists() or p.picking_type_code != 'incoming':
            return {'error': 'Receipt not found.'}
        if p.state not in ('assigned', 'confirmed'):
            return {'error': 'This receipt is not open for receiving (state: %s).'
                    % p.state}
        MoveLine = request.env['stock.move.line']
        results = []
        created = 0
        for ln in lines:
            try:
                move = request.env['stock.move'].browse(int(ln.get('move_id') or 0))
                if not move.exists() or move.picking_id.id != p.id:
                    results.append({'move_id': ln.get('move_id'), 'ok': False,
                                    'msg': 'Line not on this receipt'})
                    continue
                prod = move.product_id
                qty = float(ln.get('qty') or 0.0)
                if qty <= 0:
                    results.append({'move_id': move.id, 'ok': False,
                                    'msg': 'Quantity must be greater than 0'})
                    continue
                vals = {
                    'move_id': move.id,
                    'picking_id': p.id,
                    'product_id': prod.id,
                    'product_uom_id': move.product_uom.id,
                    'company_id': p.company_id.id,
                    'quantity': qty,
                }
                if prod.tracking in ('lot', 'serial'):
                    lot = (ln.get('lot') or '').strip()
                    if not lot:
                        results.append({'move_id': move.id, 'ok': False,
                                        'msg': 'Lot/Batch required for %s'
                                        % prod.display_name})
                        continue
                    vals['lot_name'] = lot
                if prod.use_expiration_date:
                    expiry = (ln.get('expiry') or '').strip()
                    if expiry:
                        if len(expiry) == 10:  # YYYY-MM-DD -> datetime
                            expiry = expiry + ' 23:59:59'
                        vals['expiration_date'] = expiry
                MoveLine.create(vals)
                created += 1
                results.append({'move_id': move.id, 'ok': True})
            except Exception as e:  # noqa: BLE001 - surface message to the phone
                results.append({'move_id': ln.get('move_id'), 'ok': False,
                                'msg': str(e)})
        return {'ok': True, 'created': created, 'picking': p.name,
                'results': results}
