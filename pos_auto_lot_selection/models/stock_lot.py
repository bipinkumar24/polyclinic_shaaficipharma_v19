# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Ayana KP(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import api, fields, models
from odoo.tools import float_compare


class StockLot(models.Model):
    _inherit = "stock.lot"

    is_taken = fields.Boolean(string='Taken lot', default=False,
                              help='If enables this lot number is taken')

    @api.model
    # def get_available_lots_for_pos(self, product_id):
    #     """Get available lots for a product suitable for the Point of Sale
    #     (PoS).This method retrieves the available lots for a specific product
    #     that are suitable for the Point of Sale (PoS) based on the configured
    #     removal strategy. The lots are sorted based on the expiration date or
    #     creation date,depending on the removal strategy."""
    #     company_id = self.env.company.id
    #     removal_strategy_id = (self.env['product.template'].browse(
    #         self.env['product.product'].browse(product_id).product_tmpl_id.id)
    #                            .categ_id.removal_strategy_id.method)
    #     # if removal_strategy_id == 'fefo':
    #     #     lots = self.sudo().search(
    #     #         ["&", ["product_id", "=", product_id],"&",["is_taken","=",False],
    #     #          "|", ["company_id", "=", company_id],
    #     #          ["company_id", "=", False]],
    #     #         order='expiration_date asc')
    #     # else:
    #     lots = self.sudo().search(
    #             ["&", ["product_id", "=", product_id], "|",
    #              ["company_id", "=", company_id],
    #              ["company_id", "=", False], ],
    #             order='create_date asc')
    #     lots = lots.filtered(lambda l: float_compare(l.product_qty, 0.0, precision_rounding=l.product_uom_id.rounding) > 0)[:1]
    #     lots.is_taken = True
    #     return lots.mapped("name")
    def get_available_lots_for_pos(self, product_id, location_ids=None, order_lines=None):
        company_id = self.env.company.id
        product = self.env['product.product'].browse(product_id)
        removal_strategy = (
            product.product_tmpl_id.categ_id.removal_strategy_id.method or 'fifo'
        )
        domain = [
            ("product_id", "=", product_id),
            "|",
            ("company_id", "=", company_id),
            ("company_id", "=", False),
        ]
        order_clause = (
            'expiration_date asc, create_date asc'
            if removal_strategy == 'fefo'
            else 'create_date asc'
        )
        lots = self.sudo().search(domain, order=order_clause)
        used_qty_map = {}
        if order_lines:
            for line in order_lines:
                lot_name = line.get('lot_name')
                qty = float(line.get('qty', 0))
                if lot_name:
                    used_qty_map[lot_name] = used_qty_map.get(lot_name, 0) + qty

        result = []
        for lot in lots:
            rounding = lot.product_uom_id.rounding

            quant_domain = [
                ('lot_id', '=', lot.id),
                ('product_id', '=', product_id),
                ('location_id.usage', '=', 'internal'),
            ]
            if location_ids:
                quant_domain.append(('location_id', 'in', location_ids))

            quants = self.env['stock.quant'].sudo().search(quant_domain)

            stock_qty = sum(
                (q.quantity - q.reserved_quantity)
                for q in quants
                if float_compare(
                    q.quantity - q.reserved_quantity, 0.0,
                    precision_rounding=rounding
                ) > 0
            )

            already_used = used_qty_map.get(lot.name, 0.0)
            available_qty = stock_qty - already_used

            if float_compare(available_qty, 0.0, precision_rounding=rounding) > 0:
                result.append({
                    'name': lot.name,
                    'qty': available_qty,
                    'lot_id': lot.id,
                    'stock_qty': stock_qty,
                    'already_used': already_used,
                })

        return result