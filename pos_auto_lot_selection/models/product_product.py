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
from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def get_pos_location_onhand_qty(self, product_id, location_ids):
        """Live on-hand quantity of a product in the given stock location(s).

        Fallback used by the POS when the ``stock.quant`` cache is not loaded
        into the session (so ``product.stock_quant_ids`` is unavailable), to
        avoid capping the sold quantity against missing data. Sums on-hand
        ``quantity`` (matching the load/hide metric used across the POS stock
        modules) over the location(s) and their children.
        """
        if not product_id or not location_ids:
            return 0.0
        quants = self.env["stock.quant"].search([
            ("product_id", "=", product_id),
            ("location_id", "child_of", location_ids),
        ])
        return sum(quants.mapped("quantity"))
