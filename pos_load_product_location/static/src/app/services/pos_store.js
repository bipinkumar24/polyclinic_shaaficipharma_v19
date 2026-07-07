/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

/**
 * Real-time, location-based stock visibility.
 *
 * The backend (`pos.order.sync_from_ui`) broadcasts a `PLPL_STOCK_UPDATE`
 * notification on the POS config bus channel after every order, carrying the
 * on-hand quantity — in the config's configured stock location(s) — of every
 * `product.template` that was just sold. Templates whose availability drops to
 * `<= 0` are added to a reactive Set that `getExcludedProductIds` feeds into the
 * product-grid filter (`pos_store.js:2772 filterExcludedProducts`), so
 * out-of-stock products disappear — and re-appear on refund — without reloading
 * the POS.
 *
 * Reactivity: `PosStore.constructor` returns `reactive(this)`, so inside
 * `setup` (and in the bus callback bound here) `this` is the reactive proxy;
 * mutating `plplOutOfStockTmplIds` therefore re-renders `productsToDisplay`.
 */
patch(PosStore.prototype, {
    async setup() {
        this.plplOutOfStockTmplIds = new Set();
        await super.setup(...arguments);
        this.data.connectWebSocket(
            "PLPL_STOCK_UPDATE",
            this._plplOnStockUpdate.bind(this)
        );
    },

    _plplOnStockUpdate(payload) {
        // Refresh the in-memory stock.quant records first, so every consumer of
        // `product.stock_quant_ids` (out-of-stock hiding here, the on-hand check
        // in pos_auto_lot_selection, the negative-stock guard in
        // ts_pos_stock_no_negative) sees the latest per-location quantities on
        // the next order — without reloading the POS.
        const quants = payload && payload["stock.quant"];
        if (quants && quants.length) {
            this.models.connectNewData({ "stock.quant": quants });
        }

        const availableByTmpl = (payload && payload.available_by_tmpl) || {};
        for (const [tmplId, qty] of Object.entries(availableByTmpl)) {
            const id = parseInt(tmplId, 10);
            if (!id) {
                continue;
            }
            if (qty <= 0) {
                this.plplOutOfStockTmplIds.add(id);
            } else {
                this.plplOutOfStockTmplIds.delete(id);
            }
        }
    },

    getExcludedProductIds() {
        return [...super.getExcludedProductIds(), ...this.plplOutOfStockTmplIds];
    },
});
