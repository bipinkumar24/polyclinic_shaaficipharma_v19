/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class ApproveCustomerPopup extends Component {
    static template = "pos_customer_approval_v18.ApproveCustomerPopup";
    static components = { Dialog };
    static props = {
        pendingList: Array,
        customerApprovalService: Object,
        onApproved: { type: Function, optional: true },
        getPayload: Function,
        close: Function,
    };

    setup() {
        this.state = useState({
            selectedId: this.props.pendingList[0]?.id ?? null,
            login: "",
            password: "",
            rejectReason: "",
            mode: "approve",       // "approve" | "reject"
            loading: false,
            error: "",
            successMsg: "",
            processed: [],
        });
    }

    get selected() {
        return this.props.pendingList.find(p => p.id === this.state.selectedId);
    }

    get remaining() {
        return this.props.pendingList.filter(
            p => !this.state.processed.includes(p.id)
        );
    }

    get canSubmit() {
        const { login, password, mode, rejectReason } = this.state;
        if (!login || !password) return false;
        if (mode === "reject" && !rejectReason.trim()) return false;
        return true;
    }

    selectRequest(id) {
        this.state.selectedId = id;
        this.state.error = "";
        this.state.successMsg = "";
    }

    setMode(mode) {
        this.state.mode = mode;
        this.state.error = "";
    }

    async onSubmit() {
        const s = this.state;
        s.error = "";
        s.successMsg = "";
        s.loading = true;

        try {
            let result;
            if (s.mode === "approve") {
                result = await this.props.customerApprovalService.approveActivation(
                    s.selectedId, s.login, s.password
                );
            } else {
                result = await this.props.customerApprovalService.rejectActivation(
                    s.selectedId, s.login, s.password, s.rejectReason
                );
            }

            if (result.success) {
                const label = s.mode === "approve" ? "approved" : "rejected";
                s.successMsg = `✓ ${result.partner_name || "Customer"} ${label} by ${result.approver_name}.`;
                s.processed.push(s.selectedId);
                s.password = "";
                s.rejectReason = "";

                if (s.mode === "approve" && this.props.onApproved) {
                    await this.props.onApproved();
                }

                const next = this.remaining[0];
                s.selectedId = next ? next.id : null;

                if (!next) {
                    // All processed, close the popup
                    this.props.close();
                }
            } else {
                s.error = result.error || "Operation failed.";
            }
        } catch (e) {
            s.error = "Network error. Please try again.";
            console.error("[ApproveCustomerPopup]", e);
        } finally {
            s.loading = false;
        }
    }

    async getPayload() {
        return { processed: this.state.processed };
    }
}
