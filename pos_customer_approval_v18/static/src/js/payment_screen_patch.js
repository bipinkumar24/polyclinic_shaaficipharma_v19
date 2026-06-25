/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(OrderPaymentValidation.prototype, {
    async isOrderValid(isForceValidate) {
        const baseValid = await super.isOrderValid(isForceValidate);
        if (!baseValid) {
            return false;
        }

        const hasCreditLimitMethod = this.order.payment_ids.some(
            (line) => line.payment_method_id?.check_credit_limit
        );

        if (!hasCreditLimitMethod) {
            return true;
        }

        const partner = this.order.getPartner();
        if (!partner) {
            return true;
        }

        const creditLimit = partner.pos_credit_limit || 0;
        if (creditLimit <= 0) {
            return true;
        }

        const orderTotal = this.order.priceIncl;
        const currency = this.pos.currency;
        const symbol = currency.symbol || "";
        const precision = currency.decimal_places ?? 2;

        if (orderTotal > creditLimit && partner.pos_activation_state === "approved") {
            const fmt = (v) =>
                symbol + " " + v.toFixed(precision);

            this.pos.dialog.add(AlertDialog, {
                title: _t("Credit Limit Exceeded"),
                body: _t(
                    "The order total of %(total)s exceeds the credit limit of %(limit)s " +
                    "for customer %(name)s. Please reduce the order amount or choose a " +
                    "different payment method.",
                    {
                        total: fmt(orderTotal),
                        limit: fmt(creditLimit),
                        name: partner.name,
                    }
                ),
            });
            return false;
        }
        else if(partner.pos_activation_state !== "approved") {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Customer Not Approved for Credit"),
                body: _t(
                    "The selected customer %(name)s is not approved for credit. " +
                    "Current status: %(status)s. Please select a different customer " +
                    "or payment method.",
                    {
                        name: partner.name,
                        status: _t(partner.pos_activation_state),
                    }
                ),
            });
            return false;

        }
        return true;
    },
});
