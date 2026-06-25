/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

/**
 * Extend the POS order model so a prescription reference and pharmacist
 * can be carried through to the backend pos.order record.
 */
patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        this.prescription_id = this.prescription_id || false;
        this.pharmacist_id = this.pharmacist_id || false;
    },
});

/**
 * Include pharmacy fields when building the printed receipt data.
 *
 * In Odoo 19 the per-order `export_for_printing()` model method was
 * removed; receipt payload is built by `PosStore.getOrderData(order,
 * reprint)`. We extend it the same way core modules do (e.g.
 * pos_restaurant adds `customer_count`).
 */
patch(PosStore.prototype, {
    getOrderData(order, reprint) {
        return {
            ...super.getOrderData(order, reprint),
            prescription_ref: order.prescription_ref || "",
        };
    },
});
