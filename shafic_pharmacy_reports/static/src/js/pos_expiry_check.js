/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { ExpiryNotificationPopup } from
    "@shafic_pharmacy_reports/js/pos_expiry_notification";

/**
 * Extend the POS store so that when a product with multiple
 * expiration-dated lots is added to the order, we:
 *   - Fetch its lot info via RPC (cached per session)
 *   - If 2+ lots exist AND the earliest is within expiry_alert_days,
 *     open the acknowledgment popup
 *
 * The badge on the line (shown regardless of urgency) is rendered
 * via a separate orderline patch; this file handles the popup logic.
 *
 * Caching: lot info is cached on the store keyed by product.id. The
 * cache is per browser session — when the cashier closes the POS or
 * refreshes, the cache resets, which is fine since lot data changes
 * slowly relative to a single shift.
 */
patch(PosStore.prototype, {
    setup() {
        super.setup(...arguments);
        // Map<product_id, {count, lots, expiry_alert_days}>
        this.shafic_lot_cache = new Map();
    },

    /** Fetch lot info for a product, cached. Returns null on RPC error.
     *
     * Cache key includes warehouse id because the same product may
     * have different lot pools at different branches. A cashier
     * normally stays at one warehouse for the whole session, but if
     * the config ever changes mid-session we don't want stale data.
     */
    async shafic_getLotInfo(productId) {
        const warehouseId = this.shafic_getCurrentWarehouseId();
        const cacheKey = `${productId}:${warehouseId || 0}`;
        if (this.shafic_lot_cache.has(cacheKey)) {
            return this.shafic_lot_cache.get(cacheKey);
        }
        try {
            const info = await this.data.call(
                "product.product",
                "get_lots_with_expiry",
                [productId, warehouseId || false]
            );
            this.shafic_lot_cache.set(cacheKey, info);
            return info;
        } catch (err) {
            // Don't break POS flow if lookup fails. Cashier still gets
            // the product on the order; they just don't get the popup.
            console.warn(
                "shafic_pharmacy_reports: lot lookup failed", err
            );
            return null;
        }
    },

    /** Resolve the warehouse the current POS session is selling from.
     *
     * Path: pos.config -> picking_type_id -> warehouse_id. Each hop
     * is defensive because in atypical configurations (e.g. no
     * picking_type, or picking_type without a warehouse) the chain
     * can break. Returning null means "fall back to company-wide,"
     * which is the old behavior — wrong but not broken. */
    shafic_getCurrentWarehouseId() {
        try {
            const config = this.config;
            const pickingType = config?.picking_type_id;
            const warehouse = pickingType?.warehouse_id;
            return warehouse?.id || null;
        } catch (err) {
            return null;
        }
    },

    /** Decide whether the popup should auto-open. */
    shafic_shouldAutoPopup(info) {
        if (!info || info.count < 2) return false;
        // Look at the earliest expiry; if it's within alert window, popup
        const earliest = info.lots[0];
        if (!earliest || earliest.days_to_expiry === null) return false;
        return earliest.days_to_expiry <= info.expiry_alert_days;
    },

    /** Hook addLineToOrder — Odoo 18 POS uses this for product addition.
     * We can't easily wrap the model's addLine without breaking things,
     * so we trigger off the store's higher-level method instead. */
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const line = await super.addLineToCurrentOrder(
            vals, opts, configure
        );
        if (line && line.product_id?.id) {
            this.shafic_checkExpiryAndNotify(line.product_id.id, line);
            this.shafic_checkCostSetup(line.product_id.id);
        }
        return line;
    },

    /** Layer 3 backstop: if a product reaches the till with a cost/unit
     * mismatch (cost >= price, or negative), show a NON-BLOCKING notice.
     * The sale proceeds normally; this just surfaces the problem so it
     * gets flagged for a manager. Cached per session per product so we
     * don't nag on every scan of the same item. */
    async shafic_checkCostSetup(productId) {
        if (!this.shafic_cost_checked) {
            this.shafic_cost_checked = new Set();
        }
        if (this.shafic_cost_checked.has(productId)) {
            return;
        }
        this.shafic_cost_checked.add(productId);
        try {
            const res = await this.data.call(
                "product.product", "check_cost_setup", [productId]
            );
            if (res && res.mismatch && res.message) {
                if (this.notification?.add) {
                    this.notification.add(res.message, {
                        type: "warning",
                        title: "Cost setup needs review",
                        sticky: false,
                    });
                } else if (this.env?.services?.notification?.add) {
                    this.env.services.notification.add(res.message, {
                        type: "warning",
                    });
                }
            }
        } catch (err) {
            // Never block the sale on this backstop.
            console.warn(
                "shafic_pharmacy_reports: cost check failed", err
            );
        }
    },

    /** Fire-and-forget: fetch lots, decide popup, optionally render. */
    async shafic_checkExpiryAndNotify(productId, line) {
        const info = await this.shafic_getLotInfo(productId);
        if (!info) return;

        // Store badge data on the line as plain JS properties. These
        // do NOT serialize to the server and do NOT print on the
        // receipt — they only exist in the browser's runtime for the
        // duration of the POS session. The standard POS template is
        // extended (in pos_expiry_orderline.xml) to render this data
        // visually for the cashier without touching server data.
        line._shafic_lot_count = info.count;
        line._shafic_lots = info.lots;
        if (info.count >= 2 && info.lots[0]) {
            line._shafic_badge_text =
                `⚠ ${info.count} lots · earliest expires ` +
                `${info.lots[0].expiration_date}`;
        } else {
            line._shafic_badge_text = "";
        }

        if (this.shafic_shouldAutoPopup(info)) {
            this.dialog.add(ExpiryNotificationPopup, {
                productName: line.product_id?.display_name
                    || line.product_id?.name
                    || "",
                lots: info.lots,
            });
        }
    },
});
