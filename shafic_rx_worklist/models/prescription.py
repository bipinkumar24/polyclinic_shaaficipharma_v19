# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models


class PrescriptionOrder(models.Model):
    """Pharmacy-side handoff: surface confirmed prescriptions to the
    pharmacy as a worklist and let staff mark them dispensed. No clinical
    fields are written by the pharmacy \u2014 the dispensing flags are the
    only writable data, set through a controlled action."""
    _inherit = 'prescription.order'

    acs_rx_dispensed = fields.Boolean(
        string='Dispensed', default=False, copy=False, tracking=False,
        help='Set by the pharmacy once this prescription has been '
             'dispensed at POS.')
    acs_rx_dispensed_date = fields.Datetime(
        string='Dispensed On', readonly=True, copy=False)
    acs_rx_dispensed_by = fields.Many2one(
        'res.users', string='Dispensed By', readonly=True, copy=False)
    acs_rx_member_tier = fields.Char(
        string='Member Tier', compute='_compute_acs_rx_member_tier')
    acs_rx_est_value = fields.Float(
        string='Est. Value', compute='_compute_acs_rx_est_value',
        help='Estimated pharmacy sale value of this prescription, priced '
             'per dispensing unit (e.g. per capsule), not per pack.')
    acs_rx_qr_image = fields.Binary(
        string='Handoff QR', compute='_compute_acs_rx_qr_image',
        help='QR code carrying this prescription number for the pharmacy '
             'cashier to scan at the POS.')

    # Legacy prefix still tolerated on lookup (see find_for_pos) for any
    # previously printed slips, but new QR codes carry the bare prescription
    # order number (e.g. PRO087) so the POS resolves it directly.
    _RX_QR_PREFIX = 'RX:'

    def _compute_acs_rx_member_tier(self):
        has_card = 'shafic.membership.card' in self.env
        Card = self.env['shafic.membership.card'].sudo() if has_card \
            else None
        for rec in self:
            tier = ''
            partner = rec.patient_id.partner_id
            if Card is not None and partner:
                card = Card.search([
                    ('partner_id', '=', partner.id),
                    ('state', '=', 'active')], limit=1)
                tier = (card.tier_id.name or '') if card else ''
            rec.acs_rx_member_tier = tier

    @api.depends('prescription_line_ids.acs_rx_line_value')
    def _compute_acs_rx_est_value(self):
        for rec in self:
            rec.acs_rx_est_value = sum(
                rec.prescription_line_ids.mapped('acs_rx_line_value'))

    def action_mark_dispensed(self):
        # Controlled write via sudo so pharmacy staff need only read
        # access to prescriptions, never write access to clinical data.
        self.sudo().write({
            'acs_rx_dispensed': True,
            'acs_rx_dispensed_date': fields.Datetime.now(),
            'acs_rx_dispensed_by': self.env.user.id,
        })
        return True

    def action_unmark_dispensed(self):
        self.sudo().write({
            'acs_rx_dispensed': False,
            'acs_rx_dispensed_date': False,
            'acs_rx_dispensed_by': False,
        })
        return True

    def _compute_acs_rx_qr_image(self):
        report = self.env['ir.actions.report']
        for rec in self:
            img = False
            if rec.name:
                # The QR carries the bare prescription order number so the POS
                # can scan it and load the matching prescription directly.
                payload = rec.name
                try:
                    # report.barcode() returns raw PNG bytes; a Binary field
                    # (and image_data_uri in the report) expects base64.
                    img = base64.b64encode(report.barcode(
                        'QR', payload, width=240, height=240))
                except Exception:
                    img = False
            rec.acs_rx_qr_image = img

    def action_print_slip(self):
        self.ensure_one()
        return self.env.ref(
            'shafic_rx_worklist.action_report_rx_slip').report_action(self)

    @api.model
    def find_for_pos(self, code):
        """Resolve a scanned/typed code to a pending prescription and
        return its lines priced per dispensing unit, for the POS preview
        popup. Read-only; never writes clinical data."""
        if not code:
            return {'found': False, 'error': 'empty'}
        code = code.strip()
        if code.upper().startswith(self._RX_QR_PREFIX):
            code = code[len(self._RX_QR_PREFIX):].strip()
        rx = self.sudo().search([('name', '=', code)], limit=1)
        if not rx:
            return {'found': False, 'error': 'not_found', 'code': code}
        if rx.state != 'prescription':
            return {'found': False, 'error': 'not_confirmed',
                    'code': code, 'name': rx.name}
        if rx.acs_rx_dispensed:
            return {'found': False, 'error': 'already_dispensed',
                    'code': code, 'name': rx.name}
        lines = []
        for ln in rx.prescription_line_ids:
            if not ln.product_id:
                continue
            lines.append({
                'product_id': ln.product_id.id,
                'product_name': ln.product_id.display_name,
                'qty': ln.quantity or 0.0,
                'unit_price': ln.acs_rx_unit_price,
                'line_value': ln.acs_rx_line_value,
                'qty_available': ln.product_id.qty_available,
            })
        return {
            'found': True,
            'id': rx.id,
            'name': rx.name,
            'patient': rx.patient_id.name or '',
            'physician': rx.physician_id.name or '',
            'member_tier': rx.acs_rx_member_tier or '',
            'est_value': rx.acs_rx_est_value,
            'lines': lines,
        }


class PrescriptionLine(models.Model):
    _inherit = 'prescription.line'

    acs_rx_unit_price = fields.Float(
        string='Unit Price', compute='_compute_acs_rx_value',
        help='Sale price expressed per dispensing unit (e.g. per '
             'capsule), converted natively from the product\u2019s unit '
             'of measure.')
    acs_rx_line_value = fields.Float(
        string='Line Value', compute='_compute_acs_rx_value')

    @api.depends('product_id', 'quantity')
    def _compute_acs_rx_value(self):
        for line in self:
            product = line.product_id
            unit_price = 0.0
            if product:
                price = product.list_price or 0.0
                uom = product.uom_id
                # The prescribed quantity is the number of pieces (e.g.
                # capsules = the base/reference unit of the UoM tree). Price
                # the line per piece, converting from the pack price.
                # v19: uom.category/uom_type were removed; the reference unit
                # is the root of the relative_uom_id tree (factor 1.0).
                ref = uom
                while ref and ref.relative_uom_id:
                    ref = ref.relative_uom_id
                if ref and ref.id != uom.id:
                    unit_price = uom._compute_price(price, ref)
                else:
                    unit_price = price
            line.acs_rx_unit_price = unit_price
            line.acs_rx_line_value = unit_price * (line.quantity or 0.0)
