import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(_defaultObj) {
        super.setup(...arguments);
        // It is possible that this orderline is initialized using server data,
        // meaning, it is loaded from localStorage or from server. This means
        // that some fields has already been assigned. Therefore, we only set the options
        // when the original value is falsy.
        
        //ACS: check and remove
        // if (this.prescription_order_origin_id?.shipping_date) {
        //     this.order_id.setShippingDate(this.prescription_order_origin_id.shipping_date);
        // }
    },
    get_prescription_order() {
        if (this.prescription_order_origin_id) {
            const value = {
                name: this.prescription_order_origin_id.name,
                details: this.acs_kit_details || false,
                is_kit_product: this.prescription_order_line_id && this.prescription_order_line_id.is_kit_product || false,
                kit_product_name: this.prescription_order_line_id && this.prescription_order_line_id.kit_product_name || false,
                kit_product_qty: this.prescription_order_line_id && this.prescription_order_line_id.kit_product_qty || false
            };

            return value;
        }
        return false;
    },
    /**
     * Set quantity based on the give prescription order line.
     * @param {'prescription.line'} prescriptionOrderLine
     */
    setQuantityFromPOL(prescriptionOrderLine) {
        this.setQuantity(prescriptionOrderLine.product_uom_qty);
    },
});
