/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import {
    formatFloat,
    roundDecimals as round_di,
    roundPrecision as round_pr,
    floatIsZero,
} from "@web/core/utils/numbers";


// New orders are now associated with the current table, if any.
patch(PosOrderline.prototype, {
    
    setup() {
        super.setup(...arguments);
        this.custom_uom_id = (this.get_custom_uom_id && this.get_custom_uom_id()) || (this.product_id && this.product_id.uom_id.name);    
        this.custom_uom_number_id = (this.get_custom_uom_number_id && this.get_custom_uom_number_id()) || (this.product_id && this.product_id.uom_id.id);    

    },
    
    set_custom_uom_id(uom_id) {
        this.custom_uom_id = uom_id;
        
    },
    get_custom_uom_id() {
        return this.custom_uom_id;
    },

    set_custom_uom_number_id(uom_id) {
        this.custom_uom_number_id = uom_id;
        
    },
    get_custom_uom_number_id() {
        return this.custom_uom_number_id;
    },

    get_unit() {
        return this.custom_uom_id;
    },


     export_for_printing() {
        const line = super.export_for_printing(...arguments);
        line.custom_uom_id = this.get_custom_uom_id();
        line.custom_uom_number_id = this.get_custom_uom_number_id();
        return line;
    },  



    getDisplayData() {
        return {
            ...super.getDisplayData(),
            custom_uom_id: this.get_custom_uom_id(),
            custom_uom_number_id: this.get_custom_uom_number_id(),
            unit : this.get_unit(),
        };

    },


});

