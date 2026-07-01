import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";


patch(ProductScreen.prototype, {

    async addProductToOrder(product, options = {}) {
        const is_storable = product.is_storable;
        const is_restrict_negative = this?.pos?.config?.is_restrict_negative;

        if (!is_storable || !is_restrict_negative) {
            return super.addProductToOrder(product, options);
        }
        const order = this.pos.getOrder();
        const baseUom = product.uom_id;
        const requestedQty = options.quantity || 1;

        // 🔹 Selected POS locations (all)
        const selectedLocId = this.pos.selected_stock_location_id
            ? [this.pos.selected_stock_location_id]
            : (this.pos.config.stock_location_ids || []).map(loc => loc.id);

        // No POS location configured → fall back to default behaviour.
        // (Removed a dead loop here that dereferenced product.stock_quant_ids
        //  without a guard, which threw "Cannot read properties of undefined
        //  (reading 'filter')" whenever stock_quant_ids was not loaded.)
        if (!selectedLocId.length) {
            return super.addProductToOrder(product, options);
        }

        // v19: ProductScreen.addProductToOrder receives a product.template.
        // Stock lives on the product.product *variant*, so resolve it. A
        // single-variant template is validated here; a configurable /
        // multi-variant template's variant is only known after the
        // configurator, so defer to the line-level check (PosOrderline
        // .setQuantity) and fall through.
        const variants = product.product_variant_ids || [];
        if (variants.length !== 1) {
            return super.addProductToOrder(product, options);
        }
        const variant = variants[0];

        // If per-location stock was never loaded into the POS (e.g.
        // pos_load_product_location absent), stock_quant_ids is undefined.
        // Fail open — skip the check rather than blocking every product —
        // because a missing dataset must not silently stop all sales.
        // (An empty array [] means "loaded, but no stock" and is still checked.)
        if (variant.stock_quant_ids === undefined) {
            return super.addProductToOrder(product, options);
        }

        // 🔹 Helper to safely get UoM factor
        const getUomFactor = (uom) => {
            if (!uom) return 1;
            if (typeof uom === "object") return uom.factor || 1;
            return 1;
        };

        // 🔹 Compute total quantity already in the order for this product
        let totalOrderedInBaseUom = 0;
        if (order?.lines?.length) {
            for (const line of order.lines) {
                if (line?.product_id?.id === variant.id) {
                    const lineQty = line.qty || 0;
                    // custom_uom_id is stored as a UoM *name* string; fall back
                    // to the base UoM name so the lookup still matches.
                    const lineUomName = line.custom_uom_id || baseUom.name;
                    const uom = product.models["uom.uom"].find(
                        (u) => u.name === lineUomName
                    ) || baseUom;
                    // v19: uom.uom.factor_inv was removed; `factor` now holds the
                    // absolute quantity in reference units (== v18 factor_inv).
                    const factor = uom.factor || 1;
                    const qtyInBase = lineQty * factor;
                    totalOrderedInBaseUom += qtyInBase ;
                    }
            }
        }

        // 🔹 Compute on-hand quantity for all selected locations
        // (variant-level stock only — never the template).
        let onhandQtyInLocation = 0;
        if (variant.stock_quant_ids?.length) {
            for (const quant of variant.stock_quant_ids) {
                if (selectedLocId.includes(quant.location_id?.id)) {
                    onhandQtyInLocation += quant.quantity || 0;
                }
            }
        }


        // v19: factor_inv removed → use factor (== old factor_inv).
        const av_quantity = onhandQtyInLocation * (baseUom.factor || 1)

        // 🔹 Requested quantity in base UoM
        const lineUom = options.uom || baseUom;

        let requestedQtyInBaseUom;
        if (lineUom.id === baseUom.id) {
            // Same as base UoM → convert
            requestedQtyInBaseUom = requestedQty * (baseUom.factor || 1);
        } 
        else {
            // Custom UoM → quantity is already correct, don't convert
            requestedQtyInBaseUom = requestedQty;
        }
        // 🔹 Validation
        debugger
        if ((totalOrderedInBaseUom + requestedQtyInBaseUom) > av_quantity) {
            if (variant.point_of_sale_uom && totalOrderedInBaseUom < requestedQtyInBaseUom) {
                options.quantity = 0;

                await super.addProductToOrder(product, options);

                return;
            }

            this.dialog.add(AlertDialog, {
                title: _t("Insufficient Stock"),
                body: _t(
                    `Cannot add ${requestedQty} ${lineUom.name} of ${product.name}. Available in this location: ${onhandQtyInLocation} ${baseUom.name}.`
                ),
            });
            return;
        }

        // 🔹 If validation passed, add product
        await super.addProductToOrder(product, options);
    }

});