    /** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { onMounted, useRef, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";


// IMPROVEMENT: This code is very similar to TextInputPopup.
//      Combining them would reduce the code.
// export class MultiUOMPopup extends AbstractAwaitablePopup {
export class MultiUOMPopup extends Component {
    static template = "bi_pos_multi_uom.MultiUOMPopup";
    static components = {
        Dialog,
    };
    static props = {
        list : { type: Object, optional: true },
        title: { type: String, optional: true },
        close: Function,
        };

    static template = "bi_pos_multi_uom.MultiUOMPopup";

    /**
     * @param {Object} props
     * @param {string} props.startingValue
     */
    setup() {
        super.setup();
        this.pos=usePos();
        this.state = useState({ inputValue: this.props.startingValue });
        this.inputRef = useRef("input");
        this.dialog = useService("dialog");
    }

    selectItem(itemId,item_sale_price, item_label, selected_orderline) {
        const order = this.pos.getOrder();
        if (order.getOrderlines().length > 1) {
            for (const line of order.getOrderlines()) {


                if(line.product_id.id == selected_orderline.product_id.id){
                    if(line.custom_uom_id == itemId && line.price_unit == item_sale_price){
                        if(line.price_manually_set === true){
                            var final_qty = line.qty + selected_orderline.qty;
                            line.setQuantity(final_qty);
                            this.pos.getOrder().removeOrderline(selected_orderline);

                        }
                        this.props.close();
                    }
                }
            }
        }
        selected_orderline.price_type = "manual";
        selected_orderline.setUnitPrice(item_sale_price);
        selected_orderline.set_custom_uom_id(item_label);
        selected_orderline.set_custom_uom_number_id(itemId);
        
        this.props.close();
    }

    close() {
        this.props.close();
    };
    
    
}
