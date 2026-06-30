/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
// import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { MultiUOMPopup } from "@bi_pos_multi_uom/app/uom_popup";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

// export class UOMButton extends Component {
patch(ControlButtons.prototype, {
    // static template = "bi_pos_multi_uom.UOMButton";

    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    },
    get filter_uom(){
        var list = []
        var currentOrder = this.pos.getOrder();
        var selected_line = currentOrder.getSelectedOrderline().product_id.raw.product_tmpl_id
        var selected_orderline = currentOrder.getSelectedOrderline();

        if(this.env.services.pos.point_of_sale_uom){
            for(var uom_id of this.env.services.pos.point_of_sale_uom){
                if(selected_line == uom_id.raw.product_uom_line_id){
                    if (uom_id && uom_id.unit_of_measure_id){
                        list.push({
                            id: uom_id.unit_of_measure_id.id,
                            label : uom_id.unit_of_measure_id.name,
                            sale_price : uom_id.sale_price,
                            symbol: this.env.services.pos.currency.symbol,
                            selected_orderline : selected_orderline,
                        });
                    }
                }
            }
        }
        return list;
    },

    async onClickUom() {
        const order = this.pos.getOrder();

        if (!order) {
            this.dialog.add(AlertDialog, {
                title: _t("Warning"),
                body: _t("Add Product First."),
            });
            return;
        }

        const selectedOrderline = order.getSelectedOrderline();

        if (!selectedOrderline) {
            this.dialog.add(AlertDialog, {
                title: _t("Warning"),
                body: _t("Add Product First."),
            });
            return;
        }

        const product = selectedOrderline.product_id;

        if (!product.point_of_sale_uom) {
            this.dialog.add(AlertDialog, {
                title: _t("Warning"),
                body: _t("There Is No UOM."),
            });
            return;
        }
        // debugger
        // if (!product.product_uom_ids || !product.product_uom_ids.length) {
        //     this.dialog.add(AlertDialog, {
        //         title: _t("Warning"),
        //         body: _t("There Is No Another UOM In This Product."),
        //     });
        //     return;
        // }
        await this.dialog.add(MultiUOMPopup, {
            title: _t("Product Multi UOM"),
            list: this.filter_uom,
        });
    }

})