/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { ApproveCustomerPopup } from "@pos_customer_approval_v18/js/approve_customer_popup";

patch(PartnerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.customerApprovalService = useService("pos_customer_approval");
        this.dialog = useService("dialog");
    },

    get searchDomain() {
        const base = super.searchDomain || [];
        return [...base, ["pos_allow_in_pos", "=", true]];
    },

    async onClickApproveCustomers() {
        const pendingList = await this.customerApprovalService.getPendingActivations();

        if (!pendingList || pendingList.length === 0) {
            this.dialog.add(ConfirmationDialog, {
                title: "No Pending Requests",
                body: "There are no customers waiting for POS activation.",
                confirmLabel: "OK",
                confirm: () => {},
                cancel: () => {},
            });
            return;
        }

        await makeAwaitable(this.dialog, ApproveCustomerPopup, {
            pendingList,
            customerApprovalService: this.customerApprovalService,
            onApproved: async () => {
                // Odoo 18: reload partners via POS store
                await this.pos.loadNewPartners?.();
            },
        });
    },
});
