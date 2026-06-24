/** @almightycs-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

patch(ControlButtons.prototype, {
    onClickPrescription() {
        const branchId = this.pos.config.branch_id?.id;

        const domain = [
            ["state", "=", "prescription"],
            ["acs_pos_processed", "=", false],
            ["currency_id", "=", this.pos.currency.id],
        ];

        if (branchId) {
            domain.push(["branch_id", "=", branchId]);
        }

        this.dialog.add(SelectCreateDialog, {
            resModel: "prescription.order",
            noCreate: true,
            multiSelect: false,
            domain,
            // Force the search view whose first field is the Order Number
            // (`name`) so a typed term searches by Order Number by default,
            // instead of the rx-worklist search view (Patient first).
            context: {
                search_view_ref: "acs_hms.view_hms_prescription_order_search",
            },
            onSelected: async (resIds) => {
                await this.pos.onClickPrescriptionOrder(resIds[0]);
            },
        });
    },
});
