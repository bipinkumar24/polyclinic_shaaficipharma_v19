/** @odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PosCreditLimitPopup } from "@wk_pos_credit_limit/js/PosCreditLimitPopup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        const partner = this.currentOrder.getPartner();

        if (partner && paymentMethod.type === "pay_later") {
            let hasDiscount = false;
            for (const line of this.currentOrder.getOrderlines()) {
                if (line.discount > 0) hasDiscount = true;
            }

            if (hasDiscount && partner.credit_hold_if_order_discount) {
                this.dialog.add(PosCreditLimitPopup, {
                    title: paymentMethod.name,
                    message: _t(" is on credit hold as some products have a discount."),
                    partner: partner.name,
                });
                return;
            }
        }

        return super.addNewPaymentLine(paymentMethod);
    },
});

patch(OrderPaymentValidation.prototype, {
    async askBeforeValidation() {
        const superResult = await super.askBeforeValidation();
        if (superResult === false) {
            return false;
        }

        const order = this.order;
        const partner = order.getPartner();
        if (!partner) {
            return true;
        }

        let hasDiscount = false;
        let isPayLater = false;
        let customerAccountAmount = 0;
        let customerAccountId = null;

        for (const payLine of order.payment_ids) {
            if (payLine.payment_method_id.type === "pay_later") {
                isPayLater = true;
                customerAccountAmount = payLine.amount;
                customerAccountId = payLine.payment_method_id.id;
            }
        }

        for (const line of order.getOrderlines()) {
            if (line.discount > 0) hasDiscount = true;
        }

        if (!isPayLater || customerAccountAmount <= 0) {
            return true;
        }

        try {
            const sessionCredit = await this.pos.data.call(
                "res.partner",
                "check_update_credit",
                [partner.id, this.pos.session.id, customerAccountId, customerAccountAmount],
            );

            if (partner.credit_hold) {
                this.pos.dialog.add(PosCreditLimitPopup, {
                    title: _t("Credit Hold"),
                    message: _t(" is on Credit Hold"),
                    partner: partner.name,
                });
                return false;
            }

            if (partner.block_credit_after_limit && sessionCredit > partner.wk_credit_limit) {
                this.pos.dialog.add(PosCreditLimitPopup, {
                    title: _t("Credit Limit Exceeded"),
                    message: _t(" is on credit hold as it has exceeded the credit limit."),
                    partner: partner.name,
                });
                return false;
            }

            if (partner.credit_hold_if_order_discount && hasDiscount) {
                this.pos.dialog.add(PosCreditLimitPopup, {
                    title: _t("Credit Hold Due to Discount"),
                    message: _t(" is on credit hold as the order has products with a discount."),
                    partner: partner.name,
                });
                return false;
            }

        } catch (_err) {

            if (partner.credit_hold) {
                this.pos.dialog.add(PosCreditLimitPopup, {
                    title: _t("Credit Hold (Offline)"),
                    message: _t(" is on Credit Hold."),
                    partner: partner.name,
                });
                return false;
            }

            if (
                partner.block_credit_after_limit &&
                customerAccountAmount > partner.wk_credit_limit
            ) {
                this.pos.dialog.add(PosCreditLimitPopup, {
                    title: _t("Credit Limit Exceeded (Offline)"),
                    message: _t(" is on credit hold as it has exceeded the credit limit."),
                    partner: partner.name,
                });
                return false;
            }

            if (partner.credit_hold_if_order_discount && hasDiscount) {
                this.pos.dialog.add(PosCreditLimitPopup, {
                    title: _t("Credit Hold Due to Discount (Offline)"),
                    message: _t(" is on credit hold as the order has products with a discount."),
                    partner: partner.name,
                });
                return false;
            }
        }

        return true;
    },
});