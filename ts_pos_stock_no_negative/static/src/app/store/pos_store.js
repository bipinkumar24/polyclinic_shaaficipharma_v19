import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

function buildQtyMaps(models) {
    const byProductId = new Map();
    const byTmplId    = new Map();

    const quantModel = models["stock.quant"];
    if (!quantModel) {
        console.warn("[ts_pos] stock.quant not found in POS models");
        return { byProductId, byTmplId };
    }

    const quants = typeof quantModel.getAll === "function"
        ? quantModel.getAll()
        : Object.values(quantModel.records ?? quantModel.data ?? {});

    console.log(`[ts_pos] Loaded ${quants.length} stock.quant record(s) for configured location(s)`);

    for (const quant of quants) {
        const qty  = quant.quantity ?? 0;
        if (qty <= 0) continue;

        const prod   = quant.product_id;
        if (!prod) continue;

        const prodId = typeof prod === "object" ? prod.id : prod;
        const tmplId = typeof prod === "object"
            ? (prod.product_tmpl_id?.id ?? prod.product_tmpl_id)
            : null;

        if (prodId)  byProductId.set(prodId, (byProductId.get(prodId) || 0) + qty);
        if (tmplId)  byTmplId.set(tmplId,   (byTmplId.get(tmplId)   || 0) + qty);
    }

    console.log(`[ts_pos] qty map: ${byProductId.size} product variants, ${byTmplId.size} templates`);
    return { byProductId, byTmplId };
}

patch(PosStore.prototype, {
    async afterProcessServerData() {
        const result = await super.afterProcessServerData(...arguments);
        this._applyLocationQty();
        return result;
    },

    _applyLocationQty() {
        try {
            const config = this.config;
            if (!config?.is_restrict_negative) return;

            const locs = config.stock_location_ids;
            const hasLocs = Array.isArray(locs)
                ? locs.length > 0
                : Boolean(locs?.id ?? (typeof locs === "number" ? locs : null));

            if (!hasLocs) {
                console.log("[ts_pos] No stock_location_ids configured — qty not overridden");
                return;
            }

            const { byProductId, byTmplId } = buildQtyMaps(this.models);

            const prodModel = this.models["product.product"];
            const allProds  = typeof prodModel?.getAll === "function"
                ? prodModel.getAll()
                : Object.values(prodModel?.records ?? prodModel?.data ?? {});

            for (const p of allProds) {
                if (typeof p.id !== "number") continue;
                p.qty_available = byProductId.get(p.id) ?? 0;
            }

            const tmplModel = this.models["product.template"];
            const allTmpls  = typeof tmplModel?.getAll === "function"
                ? tmplModel.getAll()
                : Object.values(tmplModel?.records ?? tmplModel?.data ?? {});

            for (const t of allTmpls) {
                if (typeof t.id !== "number") continue;
                t.qty_available = byTmplId.get(t.id) ?? 0;
            }

            console.log(
                `[ts_pos] qty_available overridden for ${allProds.length} product.product` +
                ` and ${allTmpls.length} product.template records`
            );
        } catch (e) {
            console.error("[ts_pos] _applyLocationQty error:", e);
        }
    },
});
