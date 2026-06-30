/** @odoo-module */

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";


patch(TicketScreen.prototype, {

    // v19: the previous implementation copy-overrode the whole onDoRefund() from
    // an older Odoo version. That copy drifted from core (missing is_refund,
    // pricelist_id, lot de-duplication, attribute_value_ids, PaymentScreen
    // navigation...) and used APIs removed in v19 (`set_order`, `get_partner`).
    // We now inherit the native v19 refund flow and only carry the multi-UOM
    // custom fields from each refunded line onto its newly created refund line.
    async onDoRefund() {
        await super.onDoRefund(...arguments);

        const order = this.pos.getOrder();
        if (!order) {
            return;
        }

        for (const line of order.getOrderlines()) {
            const refundedLine = line.refunded_orderline_id;
            if (refundedLine && refundedLine.custom_uom_number_id) {
                line.set_custom_uom_number_id(parseInt(refundedLine.custom_uom_number_id));
                line.set_custom_uom_id(refundedLine.custom_uom_id);
            }
        }
    },

});
