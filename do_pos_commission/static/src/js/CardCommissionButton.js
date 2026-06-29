/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
// import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";
import { SelectCommissionButton } from "./select_commission_button";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";



patch(SelectCommissionButton.prototype, {
    onClickCardCommission() {
        const pos = this.env.services.pos;
        const order = pos.getOrder();
        const currentCommission = order?.get_card_commission?.();

        // If commission exists → remove it (but keep block)
        if (currentCommission && currentCommission.id) {
            pos.set_card_commission({
                id: null,
                card_number: "",
            });
            // return;
        }


        this.env.services.dialog.add(SelectCreateDialog, {
            title: "Select Card Commission",
            resModel: "res.card.commission",
            noCreate: true,
            multiSelect: false,
            domain: [['state', '=', 'confirmed']],
            onSelected: async (ids) => {
                if (!ids || !ids.length) return;

                const commissionId = ids[0];

                const commissionModel = pos.models["res.card.commission"];
                if (!commissionModel) {
                    return;
                }

                const commission = commissionModel.get(commissionId);
                if (!commission) {
                    return;
                }

                pos.set_card_commission({
                    id: commission.id,
                    card_number: commission.card_number || "",
                });
            },
        });
    },
});