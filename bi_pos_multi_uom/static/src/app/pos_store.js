/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    
    async processServerData() {
        await super.processServerData(...arguments);
        this.point_of_sale_uom = this.models["product.template.uom.line"].getAll();
    },

});