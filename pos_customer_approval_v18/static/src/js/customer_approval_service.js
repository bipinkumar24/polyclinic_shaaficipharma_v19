/** @odoo-module **/
import { registry } from "@web/core/registry";

registry.category("services").add("pos_customer_approval", {
    name: "pos_customer_approval",
    dependencies: ["orm"],

    start(env, { orm }) {
        return {
            async getPendingActivations() {
                return await orm.call(
                    "res.partner",
                    "get_pending_pos_activations",
                    []
                );
            },

            async approveActivation(activationId, login, password) {
                return await orm.call(
                    "res.partner",
                    "approve_pos_activation",
                    [activationId, login, password]
                );
            },

            async rejectActivation(activationId, login, password, reason) {
                return await orm.call(
                    "res.partner",
                    "reject_pos_activation",
                    [activationId, login, password, reason]
                );
            },
        };
    },
});
