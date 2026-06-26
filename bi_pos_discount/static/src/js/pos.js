/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { parseFloat as oParseFloat } from "@web/views/fields/parsers";

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(...arguments);
        // 'percentage' | 'fixed' (from pos.config.discount_type)
        this.discount_line_type = this.config.discount_type;
    },

    setOptions(options) {
        this.discount_type = this.config.discount_type;
        return super.setOptions(...arguments);
    },

    setDiscount(discount) {
        const parsed_discount =
            typeof discount === "number"
                ? discount
                : isNaN(parseFloat(discount))
                ? 0
                : oParseFloat("" + discount);

        if (parsed_discount < 0) {
            this.discount = 0;
            return;
        }

        const discountType = this.discount_line_type || this.config.discount_type;
        const isFixed = discountType === "fixed" || discountType === "Fixed";
        this.discount = isFixed
            ? parsed_discount
            : Math.min(Math.max(parsed_discount, 0), 100);
    },

    prepareBaseLineForTaxesComputationExtraValues(customValues = {}) {
        const values = super.prepareBaseLineForTaxesComputationExtraValues(...arguments);
        values.discount_type =
            this.discount_line_type || this.discount_type || this.config.discount_type;
        return values;
    },
});
