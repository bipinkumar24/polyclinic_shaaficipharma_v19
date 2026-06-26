import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

function getLocationLabel(config) {
    const locs = config ? .stock_location_ids;
    if (!locs) return _t("configured location");
    if (Array.isArray(locs) && locs.length > 0) {
        return locs
            .map((l) => (typeof l === "object" ? l.complete_name || l.name : String(l)))
            .join(", ");
    }
    if (typeof locs === "object" && locs.id) {
        return locs.complete_name || locs.name || _t("configured location");
    }
    return _t("configured location");
}

function getOrderedQtyForTemplate(pos, productTmplId) {
    const order = pos.getOrder ? .();
    if (!order) return 0;
    let total = 0;
    for (const line of (order.lines ? ? [])) {
        const lineTmplId = line.product_id ? .product_tmpl_id ? .id;
        if (lineTmplId === productTmplId) {
            total += line.qty ? ? 0;
        }
    }
    return total;
}

patch(ProductScreen.prototype, {
    async addProductToOrder(product) {
        const config = this ? .pos ? .config;

        // Pass through: feature off or non-storable product
        if (!config ? .is_restrict_negative || !product ? .is_storable) {
            return await super.addProductToOrder(product);
        }

        const availableQty = product ? .qty_available ? ? 0;
        const orderedQty = getOrderedQtyForTemplate(this.pos, product.id);
        const uomName = product ? .uom_id ? .name || "Unit";
        const locLabel = getLocationLabel(config);

        if (orderedQty >= availableQty) {
            this.dialog.add(AlertDialog, {
                title: _t("Insufficient Stock"),
                body: _t(
                    "Cannot add 1 %(name)s. Available in this location: %(avail)s %(uom)s.", {
                        name: product.display_name || product.name,
                        avail: availableQty,
                        uom: uomName,
                    }
                ),
            });
            return;
        }

        return await super.addProductToOrder(product);
    },
});