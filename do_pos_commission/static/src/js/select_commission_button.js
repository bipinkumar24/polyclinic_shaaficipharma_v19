/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class SelectCommissionButton extends Component {
    static template = "do_pos_commission.SelectCommissionButton";
    static props = ["card_commission?"];
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    }
}
