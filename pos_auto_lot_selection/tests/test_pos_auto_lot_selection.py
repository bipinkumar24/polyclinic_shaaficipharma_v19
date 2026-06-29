# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
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
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.fields import Datetime
from datetime import timedelta


@tagged('post_install', '-at_install')
class TestPosAutoLotSelection(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPosAutoLotSelection, cls).setUpClass()

        # Create a product with tracking enabled
        cls.product = cls.env['product.product'].create({
            'name': 'POS Tracked Product',
            'type': 'consu',
            'is_storable': True,
            'tracking': 'lot',
        })

        # Find or create a stock location for updating quants
        cls.warehouse = cls.env['stock.warehouse'].search([
            ('company_id', '=', cls.env.company.id)
        ], limit=1)
        if cls.warehouse:
            cls.stock_location = cls.warehouse.lot_stock_id
        else:
            cls.stock_location = cls.env['stock.location'].search([
                ('usage', '=', 'internal')
            ], limit=1)

    def _add_quantity_to_lot(self, lot, qty, location=None):
        """Helper to set quantity for a lot using stock.quant."""
        return self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': (location or self.stock_location).id,
            'lot_id': lot.id,
            'quantity': qty,
            'company_id': self.env.company.id,
        })

    def test_no_lots_returns_empty(self):
        """No lots exist at all for the product -> empty list."""
        new_product = self.env['product.product'].create({
            'name': 'Another Tracked Product',
            'type': 'consu',
            'is_storable': True,
            'tracking': 'lot',
        })
        res = self.env['stock.lot'].get_available_lots_for_pos(new_product.id)
        self.assertEqual(res, [], "Should return empty list when no lots exist")

    def test_lot_with_no_quant_is_excluded(self):
        """A lot exists but has no stock.quant (zero qty) -> excluded."""
        self.env['stock.lot'].create({
            'name': 'LOT-NO-QTY',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        res = self.env['stock.lot'].get_available_lots_for_pos(self.product.id)
        self.assertEqual(res, [], "Lot with zero available quantity should not be returned")

    def test_fefo_orders_by_expiration_date(self):
        """FEFO removal strategy -> lots ordered by soonest expiration_date first."""
        product_categ = self.product.product_tmpl_id.categ_id
        fefo_strategy = self.env['product.removal'].search(
            [('method', '=', 'fefo')], limit=1
        )
        if fefo_strategy:
            product_categ.removal_strategy_id = fefo_strategy.id

        lot_far = self.env['stock.lot'].create({
            'name': 'LOT-EXP-FAR',
            'product_id': self.product.id,
            'expiration_date': Datetime.now() + timedelta(days=10),
            'company_id': self.env.company.id,
        })
        lot_soon = self.env['stock.lot'].create({
            'name': 'LOT-EXP-SOON',
            'product_id': self.product.id,
            'expiration_date': Datetime.now() + timedelta(days=2),
            'company_id': self.env.company.id,
        })
        lot_mid = self.env['stock.lot'].create({
            'name': 'LOT-EXP-MID',
            'product_id': self.product.id,
            'expiration_date': Datetime.now() + timedelta(days=5),
            'company_id': self.env.company.id,
        })

        self._add_quantity_to_lot(lot_far, 10.0)
        self._add_quantity_to_lot(lot_soon, 10.0)
        self._add_quantity_to_lot(lot_mid, 10.0)

        res = self.env['stock.lot'].get_available_lots_for_pos(self.product.id)
        returned_names = [r['name'] for r in res]

        if fefo_strategy:
            self.assertEqual(
                returned_names,
                [lot_soon.name, lot_mid.name, lot_far.name],
                "FEFO should order lots by soonest expiration date first",
            )
        else:
            # FEFO removal strategy not available in this DB; fall back to
            # asserting all three lots are at least present with correct qty.
            self.assertEqual(set(returned_names),
                              {lot_far.name, lot_soon.name, lot_mid.name})

        for entry in res:
            self.assertEqual(entry['qty'], 10.0)
            self.assertEqual(entry['already_used'], 0.0)

    def test_fifo_fallback_orders_by_create_date(self):
        """No FEFO strategy configured -> falls back to FIFO (create_date asc)."""
        lot_old = self.env['stock.lot'].create({
            'name': 'LOT-OLD',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        lot_new = self.env['stock.lot'].create({
            'name': 'LOT-NEW',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })

        self._add_quantity_to_lot(lot_old, 5.0)
        self._add_quantity_to_lot(lot_new, 5.0)

        res = self.env['stock.lot'].get_available_lots_for_pos(self.product.id)
        returned_names = [r['name'] for r in res]

        self.assertEqual(
            returned_names,
            [lot_old.name, lot_new.name],
            "FIFO fallback should order lots by oldest create_date first",
        )

    def test_order_lines_nets_off_already_used_quantity(self):
        """Quantity already allocated to a lot in the current cart (order_lines)
        is subtracted from what's offered, and a fully-consumed lot is excluded."""
        lot = self.env['stock.lot'].create({
            'name': 'LOT-CART',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        self._add_quantity_to_lot(lot, 10.0)

        # Partial consumption in the current cart.
        res = self.env['stock.lot'].get_available_lots_for_pos(
            self.product.id,
            order_lines=[{'lot_name': lot.name, 'qty': 4}],
        )
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['stock_qty'], 10.0)
        self.assertEqual(res[0]['already_used'], 4.0)
        self.assertEqual(res[0]['qty'], 6.0)

        # Full consumption in the current cart -> lot no longer offered.
        res_full = self.env['stock.lot'].get_available_lots_for_pos(
            self.product.id,
            order_lines=[{'lot_name': lot.name, 'qty': 10}],
        )
        self.assertEqual(res_full, [],
                          "Lot fully allocated within the cart should be excluded")

    def test_location_ids_filters_quants(self):
        """Passing location_ids restricts stock to quants in those locations."""
        other_location = self.env['stock.location'].create({
            'name': 'Other Internal Location',
            'usage': 'internal',
            'location_id': self.stock_location.location_id.id,
        })
        lot = self.env['stock.lot'].create({
            'name': 'LOT-MULTI-LOC',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        self._add_quantity_to_lot(lot, 7.0, location=self.stock_location)
        self._add_quantity_to_lot(lot, 3.0, location=other_location)

        # No filter -> both quants counted.
        res_all = self.env['stock.lot'].get_available_lots_for_pos(self.product.id)
        self.assertEqual(res_all[0]['qty'], 10.0)

        # Filtered to only the primary stock location.
        res_filtered = self.env['stock.lot'].get_available_lots_for_pos(
            self.product.id, location_ids=[self.stock_location.id]
        )
        self.assertEqual(res_filtered[0]['qty'], 7.0)
