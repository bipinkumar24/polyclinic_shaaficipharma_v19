import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    /**
     * A line is "sold per pc" when its unit of measure is the product's
     * configured `uom_for_per_pc`. During a prescription settle the per-piece
     * UOM is stored on the line as `custom_uom_number_id` (see bi_pos_multi_uom
     * / acs_hms_pharmacy_pos).
     */
    isSoldPerPc() {
        const product = this.product_id;
        if (!product || !product.uom_for_per_pc || !this.custom_uom_number_id) {
            return false;
        }
        const perPcUomId = product.uom_for_per_pc.id ?? product.uom_for_per_pc;
        return Number(this.custom_uom_number_id) === Number(perPcUomId);
    },

    /**
     * Per-pc lines are deducted from on-hand by an automatic (FIFO) lot pick on
     * the backend picking, so the cashier never selects a lot. Report the line
     * as having a valid lot to keep the payment screen from warning about
     * missing serial/lot numbers.
     */
    hasValidProductLot() {
        if (this.isSoldPerPc()) {
            return true;
        }
        return super.hasValidProductLot(...arguments);
    },

    /**
     * Prevent the per-pc line from being treated as lot tracked in the POS UI
     * (lot popups, merge restrictions); lot assignment happens on the backend.
     */
    isLotTracked() {
        if (this.isSoldPerPc()) {
            return false;
        }
        return super.isLotTracked(...arguments);
    },
});
