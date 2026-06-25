/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

patch(ControlButtons.prototype, {
    onClickRxHandoff() {
        this.pos.shaficOpenRxPopup();
    },
});
