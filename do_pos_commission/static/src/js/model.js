import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosStore } from "@point_of_sale/app/services/pos_store";


// patch(PosStore.prototype, {
// 	set_card_commission(commission) {
//         this.commission = commission;
//         this.get_order().update({
//                 card_commission_id: commission.id,
//             });

//     },

//     get_card_commission() {
//         return this.commission || false;
//     },

//     export_as_JSON() {
//         const json = super.export_as_JSON(...arguments);
//         json.card_commission = this.card_commission || false;
//         return json;
//     },

//     init_from_JSON(json) {
//         super.init_from_JSON(...arguments);
//         this.card_commission = json.card_commission || false;
//     },
	
// });




patch(PosOrder.prototype, {
    set_card_commission(commission) {
        debugger
        this.assertEditable();
        // this.card_commission = commission;
        // this.update({card_commission:commission});
        this.card_commission = commission || false;
    },

    get_card_commission() {
        return this.card_commission || false;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.card_commission = this.card_commission || false;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.card_commission = json.card_commission || false;
    },
});




patch(PosStore.prototype, {
    set_card_commission(commission) {
        const order = this.getOrder();
        this.commission = commission;
        this.getOrder().update({
                card_commission_id: commission.id,
            });

        if (!order) return;

        order.set_card_commission(commission);
        // order.get_card_commission();
    },

    get_card_commission() {
        const order = this.getOrder();
        return order ? order.get_card_commission() : false;
    },
});

