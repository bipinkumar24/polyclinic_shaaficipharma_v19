import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";

function roundToCurrency(value, decimalPlaces) {
    const factor = Math.pow(10, decimalPlaces);
    const epsilon = value >= 0 ? 1e-9 : -1e-9;
    return Math.round(value * factor + epsilon) / factor;
}

function priceUnitForTaxIncludedTarget(targetIncl, taxRate, decimalPlaces) {
    const step = Math.pow(10, -decimalPlaces);
    const evalTotal = (priceUnit) =>
        roundToCurrency(
            priceUnit + roundToCurrency(priceUnit * taxRate, decimalPlaces),
            decimalPlaces
        );

    const naive = roundToCurrency(targetIncl / (1 + taxRate), decimalPlaces);
    const candidates = [
        naive,
        roundToCurrency(naive - step, decimalPlaces),
        roundToCurrency(naive + step, decimalPlaces),
    ];

    let best = candidates[0];
    let bestDiff = Math.abs(evalTotal(candidates[0]) - targetIncl);
    for (const candidate of candidates.slice(1)) {
        const diff = Math.abs(evalTotal(candidate) - targetIncl);
        if (diff < bestDiff) {
            bestDiff = diff;
            best = candidate;
        }
    }
    return best;
}

patch(ControlButtons.prototype, {
    async showingPercentage() {
        this.dialog.add(NumberPopup, {
            title: _t("Discount Percentage"),
            startingValue: this.pos.config.discount_pc,
            getPayload: (num) => {
                const val = Math.max(
                    0,
                    Math.min(100, this.env.utils.parseValidFloat(num.toString()))
                );
                this.apply_discount(val);
            },
        });
    },
    async showingAmount() {
        this.dialog.add(NumberPopup, {
            title: _t("Discount Amount"),
            startingValue: this.pos.config.discount_pc,
            getPayload: (num) => {
                const val = this.env.utils.parseValidFloat(num.toString());
                this.apply_discount_amount(val);
            },
        });
    },
    async clickGlobalDiscount() {
        if (this.pos.user?.is_user_pos_discount) {
            return;
        }
        if (this.pos.config.global_discount_type == "percentage") {
            this.dialog.add(NumberPopup, {
                title: _t("Discount Percentage"),
                startingValue: this.pos.config.discount_pc,
                getPayload: (num) => {
                    const val = Math.max(
                        0,
                        Math.min(100, this.env.utils.parseValidFloat(num.toString()))
                    );
                    this.apply_discount(val);
                },
            });
        } else if (this.pos.config.global_discount_type == "amount") {
            this.dialog.add(NumberPopup, {
                title: _t("Discount Amount"),
                startingValue: this.pos.config.discount_pc,
                getPayload: (num) => {
                    const val = Math.max(
                        0,
                        Math.min(100, this.env.utils.parseValidFloat(num.toString()))
                    );
                    this.apply_discount_amount(val);
                },
            });
        } else {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Select Discount Type"),
                body: _t("Please select the type of global discount to be applied"),
                cancel: true,
                confirmLabel: "Percentage",
                cancelLabel: "Amount",
                confirm: () => this.showingPercentage(),
                cancel: () => this.showingAmount(),
            });
        }
    },
 
    _getDiscountableLinesByTax(order, discountProduct) {
        const groups = new Map();
        const lines = order
            .getOrderlines()
            .filter(
                (line) =>
                    line.isGlobalDiscountApplicable() &&
                    line.getProduct().id !== discountProduct.id
            );

        for (const line of lines) {
            const taxIds = (line.tax_ids || [])
                .map((tax) => tax.id)
                .sort((a, b) => a - b);
            const key = taxIds.join("_");
            if (!groups.has(key)) {
                groups.set(key, { taxIds, lines: [], base: 0 });
            }
            const group = groups.get(key);
            group.lines.push(line);
            group.base += line.priceExcl;
        }
        return [...groups.values()];
    },
    async apply_discount_amount(pc) {
        const order = this.pos.getOrder();
        const product = this.pos.config.global_discount_product_id;

        if (!product) {
            this.dialog.add(AlertDialog, {
                title: _t("No discount product found"),
                body: _t(
                    "The discount product seems misconfigured. Make sure it is flagged as 'Can be Sold' and 'Available in Point of Sale'."
                ),
            });
            return;
        }
        order
            .getOrderlines()
            .filter((line) => line.getProduct().id === product.id)
            .forEach((line) => line.delete());

        const groups = this._getDiscountableLinesByTax(order, product);
        const totalBase = groups.reduce((sum, group) => sum + group.base, 0);
        if (totalBase <= 0) {
            return;
        }

        const decimalPlaces = this.pos.currency?.decimal_places ?? 2;

        let allocatedSoFar = 0;
        for (const [index, group] of groups.entries()) {
            const isLastGroup = index === groups.length - 1;
            const rawShare = (group.base / totalBase) * pc;
            const groupShareIncl = isLastGroup
                ? roundToCurrency(pc - allocatedSoFar, decimalPlaces)
                : roundToCurrency(rawShare, decimalPlaces);
            allocatedSoFar = roundToCurrency(allocatedSoFar + groupShareIncl, decimalPlaces);

            const discount = -groupShareIncl;

            if (discount < 0) {
                await this.pos.addLineToCurrentOrder(
                    {
                        product_id: product,
                        product_tmpl_id: product.product_tmpl_id,
                        price_unit: discount,
                        tax_ids: [],
                    },
                    { merge: false }
                );
            }
        }
    },
    async apply_discount(pc) {
        const order = this.pos.getOrder();
        const product = this.pos.config.global_discount_product_id;

        if (!product) {
            this.dialog.add(AlertDialog, {
                title: _t("No discount product found"),
                body: _t(
                    "The discount product seems misconfigured. Make sure it is flagged as 'Can be Sold' and 'Available in Point of Sale'."
                ),
            });
            return;
        }
        order
            .getOrderlines()
            .filter((line) => line.getProduct().id === product.id)
            .forEach((line) => line.delete());

        const groups = this._getDiscountableLinesByTax(order, product);
        for (const group of groups) {
            const taxes = group.taxIds
                .map((taxId) => this.pos.models["account.tax"].get(taxId))
                .filter(Boolean);

            const discount = (-pc / 100.0) * group.base;
            if (discount < 0) {
                await this.pos.addLineToCurrentOrder(
                    {
                        product_id: product,
                        product_tmpl_id: product.product_tmpl_id,
                        price_unit: discount,
                        tax_ids: taxes.map((tax) => ["link", tax]),
                    },
                    { merge: false }
                );
            }
        }
    },
});
