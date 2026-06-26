import { accountTaxHelpers } from "@account/helpers/account_tax";
import { patch } from "@web/core/utils/patch";
import { roundPrecision } from "@web/core/utils/numbers";

patch(accountTaxHelpers, {
    add_tax_details_in_base_line(base_line, company, { rounding_method = null } = {}) {
        rounding_method = rounding_method || company.tax_calculation_rounding_method;

        const discount = base_line.discount || 0;
        const discount_type = base_line.discount_type;
        let price_unit_after_discount;
        if (discount > 0 && (discount_type === "fixed" || discount_type === "Fixed")) {
            // Fixed amount discount: subtract it from the whole line total.
            const quantity = base_line.quantity || 1;
            const base_total = base_line.price_unit * quantity;
            price_unit_after_discount = (base_total - discount) / quantity;
        } else {
            // Standard percentage discount (core behaviour).
            price_unit_after_discount = base_line.price_unit * (1 - discount / 100.0);
        }

        const currency_pd = base_line.currency_id.rounding;
        const company_currency_pd = company.currency_id.rounding;
        const taxes_computation = this.get_tax_details(
            base_line.tax_ids,
            price_unit_after_discount,
            base_line.quantity,
            {
                precision_rounding: currency_pd,
                rounding_method: rounding_method,
                product: base_line.product_id,
                product_uom: base_line.product_uom_id,
                special_mode: base_line.special_mode,
                filter_tax_function: base_line.filter_tax_function,
            }
        );

        const rate = base_line.rate;
        const tax_details = (base_line.tax_details = {
            raw_total_excluded_currency: taxes_computation.total_excluded,
            raw_total_excluded: rate ? taxes_computation.total_excluded / rate : 0.0,
            raw_total_included_currency: taxes_computation.total_included,
            raw_total_included: rate ? taxes_computation.total_included / rate : 0.0,
            taxes_data: [],
        });

        if (rounding_method === "round_per_line") {
            tax_details.raw_total_excluded = roundPrecision(
                tax_details.raw_total_excluded,
                currency_pd
            );
            tax_details.raw_total_included = roundPrecision(
                tax_details.raw_total_included,
                currency_pd
            );
        }

        for (const tax_data of taxes_computation.taxes_data) {
            let tax_amount = rate ? tax_data.tax_amount / rate : 0.0;
            let base_amount = rate ? tax_data.base_amount / rate : 0.0;

            if (rounding_method === "round_per_line") {
                tax_amount = roundPrecision(tax_amount, company_currency_pd);
                base_amount = roundPrecision(base_amount, company_currency_pd);
            }

            tax_details.taxes_data.push({
                ...tax_data,
                raw_tax_amount_currency: tax_data.tax_amount,
                raw_tax_amount: tax_amount,
                raw_base_amount_currency: tax_data.base_amount,
                raw_base_amount: base_amount,
            });
        }
    },
});
