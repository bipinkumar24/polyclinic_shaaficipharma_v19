# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    """Enforce data-quality rules at goods receipt confirmation.

    Hooks into ``button_validate`` for incoming pickings (receipts).
    When the configured settings require a field, the receipt cannot be
    confirmed until all of its products have that field. This catches
    data hygiene problems at source — much more reliable than asking the
    team to clean up records after the fact.

    The checks fire only for incoming pickings (typically vendor
    receipts). Internal transfers and customer deliveries pass through
    unchanged.
    """
    _inherit = 'stock.picking'

    pharmacy_receiving_issues = fields.Text(
        string='Receiving Data Issues', compute='_compute_pharmacy_issues',
        help='Real-time check of the receipt against the active '
             'receiving-data rules. Empty when the receipt is clean.')

    def _is_pharmacy_receipt(self):
        """True for incoming pickings."""
        self.ensure_one()
        return (self.picking_type_id and
                self.picking_type_id.code == 'incoming')

    @api.depends('move_ids', 'move_ids.product_id',
                 'move_ids.product_id.barcode',
                 'move_ids.product_id.default_code',
                 'move_line_ids', 'move_line_ids.lot_id',
                 'move_line_ids.lot_name', 'state')
    def _compute_pharmacy_issues(self):
        for picking in self:
            if not picking._is_pharmacy_receipt():
                picking.pharmacy_receiving_issues = False
                continue
            issues = picking._collect_pharmacy_receiving_issues()
            picking.pharmacy_receiving_issues = (
                '\n'.join(issues) if issues else False)

    def _collect_pharmacy_receiving_issues(self):
        """Return the list of issues found on this receipt.

        Empty list means the receipt is clean. The same routine is used
        for the on-form warning column and the block-on-validate check,
        so the user sees exactly what would stop the confirmation.
        """
        self.ensure_one()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        require_barcode = get_param(
            'shafic_pharmacy_reports.receiving_require_barcode',
            'True') in ('True', '1', True)
        require_ref = get_param(
            'shafic_pharmacy_reports.receiving_require_ref',
            'True') in ('True', '1', True)
        require_expiry = get_param(
            'shafic_pharmacy_reports.receiving_require_expiry',
            'True') in ('True', '1', True)
        require_lot = get_param(
            'shafic_pharmacy_reports.receiving_require_lot',
            'True') in ('True', '1', True)

        DataRule = self.env['pharmacy.data.rule']
        issues = []
        seen_products = set()

        for move in self.move_ids:
            product = move.product_id
            if not product or product.id in seen_products:
                continue
            seen_products.add(product.id)
            label = product.display_name or product.name or 'Unknown product'
            if require_barcode and not DataRule.value_is_valid(
                    'barcode', product.barcode):
                issues.append(_(
                    '%s — barcode is missing or invalid.') % label)
            if require_ref and not DataRule.value_is_valid(
                    'default_code', product.default_code):
                issues.append(_(
                    '%s — internal reference is missing or invalid.') % label)

        if require_lot or require_expiry:
            for ml in self.move_line_ids:
                product = ml.product_id
                if not product or product.tracking not in ('lot', 'serial'):
                    continue
                label = product.display_name or product.name
                lot = ml.lot_id
                lot_name = ml.lot_name or (lot.name if lot else False)
                if require_lot:
                    if not lot and not lot_name:
                        issues.append(_(
                            '%s — lot/batch is missing on a receipt '
                            'line.') % label)
                    elif lot_name and not DataRule.value_is_valid(
                            'lot_name', lot_name):
                        issues.append(_(
                            '%s — lot/batch "%s" does not meet the '
                            'data quality rule.') % (label, lot_name))
                if require_expiry:
                    if lot and not lot.expiration_date:
                        issues.append(_(
                            '%s — expiry date is missing on lot %s.')
                            % (label, lot.name))
                    elif (not lot) and lot_name:
                        # New lot not yet created — Odoo creates it on
                        # validate; we cannot check the expiry yet but
                        # require the user to set it before confirming.
                        issues.append(_(
                            '%s — expiry date is required for new lot '
                            '%s; create the lot record with an expiry '
                            'first.') % (label, lot_name))

        return issues

    def button_validate(self):
        """Override: block confirmation when issues exist and the
        block-mode setting is on; warn otherwise."""
        block_mode = self.env['ir.config_parameter'].sudo().get_param(
            'shafic_pharmacy_reports.receiving_block',
            'False') in ('True', '1', True)
        if block_mode:
            for picking in self:
                if not picking._is_pharmacy_receipt():
                    continue
                issues = picking._collect_pharmacy_receiving_issues()
                if issues:
                    sample = '\n  • '.join(issues[:8])
                    more = (
                        '\n  • ...and %d more' % (len(issues) - 8)
                        if len(issues) > 8 else '')
                    raise UserError(_(
                        'This receipt cannot be confirmed because some '
                        'products are missing required data.\n\n  • %s%s'
                        '\n\nFix the data on the product or lot records, '
                        'or ask a Pharmacy Admin to turn off the '
                        'receiving-checklist block in Settings.'
                    ) % (sample, more))
        return super().button_validate()
