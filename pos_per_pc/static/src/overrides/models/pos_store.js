import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    /**
     * When settling a prescription order, if a product is configured with a
     * per-piece price/UOM (Sales Price Per Pc + UOM for Per Pc), use those
     * values for the price and unit of measure of the generated POS line.
     *
     * We adjust the prescription lines in place before delegating to the
     * original implementation, which already reads `price_unit` and
     * `product_uom` from each line when building the order line.
     */
    async settlePrescriptionSO(prescription_order, orderFiscalPos) {
        for (const line of prescription_order.prescription_line_ids) {
            const product = line.product_id;
            if (product && product.sales_price_per_pc && product.uom_for_per_pc) {
                line.price_unit = product.sales_price_per_pc;
                line.product_uom = product.uom_for_per_pc;
            }
        }
        const result = await super.settlePrescriptionSO(prescription_order, orderFiscalPos);

        // Per-pc lines are deducted from on-hand by a FIFO lot pick on the
        // backend picking, so drop any lots the settle routine auto-attached
        // and keep the POS line lot-free (no lot warning at payment).
        for (const orderline of this.getOrder().lines) {
            if (orderline.isSoldPerPc?.() && orderline.pack_lot_ids?.length) {
                orderline.update({ pack_lot_ids: [["unlink", ...orderline.pack_lot_ids]] });
            }
        }
        return result;
    },
});
