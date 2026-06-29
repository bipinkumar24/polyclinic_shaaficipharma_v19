/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectCommissionButton } from "./select_commission_button";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },

    get card_commission() {
        return this.pos.getOrder()?.get_card_commission() || false;
    },
});

patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        SelectCommissionButton,
    },
});
