import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosOrderline.prototype, {
    
    setQuantity(quantity, keep_price) {
        const config = this?.order_id?.config_id;
        const product = this?.product_id;
        const order = this.order_id;

        if (!config?.is_restrict_negative || !product?.is_storable || !quantity) {
            return super.setQuantity(quantity, keep_price);
        }

        if (!order || !product) {
            return super.setQuantity(quantity, keep_price);
        }
        // Base UoM of product (Box)
        const baseUom = product.uom_id;
        // Current line UoM (PC or Box). custom_uom_id is stored as a UoM *name*
        // string; fall back to the base UoM name so the lookup still matches.
        const lineUomName = this.custom_uom_id || baseUom.name;
        const uom = this.models["uom.uom"].find((dp) => dp.name === lineUomName) || baseUom;
        // 🔹 Selected POS locations
        const selectedLocIds = order.config.selected_stock_location_id
            ? [order.config.selected_stock_location_id]
            : (order.config.stock_location_ids || []).map(loc => loc.id);

        // Fail open if per-location stock was never loaded (undefined) or no
        // location is configured — a missing dataset must not block edits.
        // ([] means "loaded, no stock" and is still validated below.)
        if (product.stock_quant_ids === undefined || !selectedLocIds.length) {
            return super.setQuantity(quantity, keep_price);
        }

        const qtyAvailable = product.stock_quant_ids
            .filter(q => selectedLocIds.includes(q.location_id?.id))
            .reduce((sum, q) => sum + (q.quantity || 0), 0);
        // v19: uom.uom.factor_inv was removed; `factor` now holds the absolute
        // quantity in reference units (== v18 factor_inv).
        const onhendqty = qtyAvailable * (baseUom.factor || 1);
        const is_restrict_negative = this?.order_id?.config_id?.is_restrict_negative
        const is_storable = this?.product_id?.is_storable
        let orderedInBaseUom = quantity;
        let totalOrderedInBaseUom = 0;


        // 🔹 LOOP through order lines
        for (const line of order.lines) {
            if(line.id != this.id){
                if (line.product_id && line.product_id.id == product.id) 
                    {
                    let lineUomName = line.custom_uom_id || baseUom.name;

                    let lineQty = line.qty;
                    let lineUomRec = product.models["uom.uom"].find(
                        (u) => u.name === lineUomName
                    ) || baseUom;
                    let factor = lineUomRec.factor || 1;

                    // 🔹 Convert to base UoM
                    if (lineQty != 0){
                        totalOrderedInBaseUom += lineQty * factor;
                    }}
                }
            }
        totalOrderedInBaseUom += (quantity * (uom.factor || 1)) ;
        debugger
        if (totalOrderedInBaseUom)
            if (totalOrderedInBaseUom > onhendqty) {
                return {
                    title: _t("Insufficient Stock"),
                    body: _t(
                        `Stock limit reached for ${product.display_name}.
            Available: ${qtyAvailable} ${baseUom.name}
            Ordered: ${totalOrderedInBaseUom} ${uom.name}`
                        ),
                    };
                    return;
                }
        if (uom.name !== baseUom.name) {
            let av_quantity = onhendqty
            let UomFactor = uom.factor;
            if (UomFactor)
            {
                av_quantity = (av_quantity * UomFactor)
            }
            if (is_restrict_negative && is_storable && (qtyAvailable <= 0 || (totalOrderedInBaseUom) > av_quantity)) {
            return {
                title: _t("Insufficient Stock"),
                body: _t(
                    `Stock limit reached for ${product.name}. Available quantity: ${totalOrderedInBaseUom/(baseUom.factor || 1)} ${uom.name}.`
                ),
            };

        }
        // Save quantity as entered (line UoM)
        return super.setQuantity(quantity, keep_price);
        }
        else {
            // Save quantity as entered (line UoM)
            return super.setQuantity(quantity, keep_price);
        }
        
    },

});






// patch(PosOrderline.prototype, {

//     set_quantity(quantity, keep_price) {
//         const is_restrict_negative = this?.order_id?.config_id?.is_restrict_negative
//         const qty_available = this?.product_id?.qty_available
//         const is_storable = this?.product_id?.is_storable
//         if (is_restrict_negative && is_storable && quantity && (qty_available <= 0 || quantity > qty_available)){
//             return {
//                     title: _t("Insufficient Stock"),
//                     body: _t(
//                         `Stock limit reached for ${this?.product_id?.name}. Available quantity: ${qty_available}.`
//                     ),
//                 };
//         }
//         else {
//             return super.set_quantity(quantity, keep_price);
//         }
//     },
// });
