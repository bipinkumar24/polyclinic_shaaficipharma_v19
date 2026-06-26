import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosOrderline.prototype, {
    setQuantity(quantity, keep_price) {
        const config = this.order_id ? .config_id;
        const product = this.product_id;
        const tmpl = product ? .product_tmpl_id;

        if (!config ? .is_restrict_negative || !tmpl ? .is_storable) {
            return super.setQuantity(quantity, keep_price);
        }

        const available = tmpl ? .qty_available ? ? product ? .qty_available ? ? 0;
        const uomName = product ? .uom_id ? .name || tmpl ? .uom_id ? .name || "Units";

        const quant = typeof quantity === "number" ?
            quantity :
            parseFloat("" + (quantity ? quantity : 0));

        if (!isNaN(quant) && quant > available) {
            return {
                title: _t("Insufficient Stock"),
                body: _t(
                    "Stock limitz reached for %(name)s.\nAvailable: %(avail)s %(uom)s\nRequested: %(qty)s %(uom)s", {
                        name: tmpl ? .display_name || product ? .display_name || "",
                        avail: available,
                        qty: quant,
                        uom: uomName,
                    }
                ),
            };
        }

        return super.setQuantity(quantity, keep_price);
    },
});