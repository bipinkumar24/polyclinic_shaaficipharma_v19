/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { RxScanPopup } from "@shafic_rx_worklist/app/rx_scan_popup";

patch(PosStore.prototype, {
    /** RPC: resolve a scanned/typed code to a pending prescription. */
    async shaficLookupRx(code) {
        try {
            return await this.data.call(
                "prescription.order", "find_for_pos", [code]);
        } catch (e) {
            return { found: false, error: "rpc" };
        }
    },

    /**
     * Handle a hardware/camera scan of a prescription QR (a bare order
     * number, e.g. PRO087). Resolve it and, when it is a usable pending
     * prescription, load it straight into the current order through the rich
     * settle flow so per-piece pricing and lot handling apply. Anything that
     * is not a prescription falls back to the standard unknown-barcode notice.
     *
     * @param {Object} parsed parsed barcode ({ code, ... }) from the reader
     * @returns {Promise<boolean>} true when a prescription was loaded
     */
    async shaficScanRx(parsed) {
        const code = (parsed?.code || "").trim();
        if (!code) {
            return false;
        }
        const result = await this.shaficLookupRx(code);
        if (result && result.found) {
            // Rich settle flow (acs_hms_pharmacy_pos), no confirmation prompt.
            if (this.onClickPrescriptionOrder) {
                await this.onClickPrescriptionOrder(result.id, { skipPrompt: true });
            } else {
                // Fallback for installs without the rich settle flow.
                await this.shaficAddRxToOrder(result);
            }
            this.notification.add(
                _t("Prescription %s loaded.", result.name || code),
                { type: "success" }
            );
            return true;
        }
        const error = result && result.error;
        if (error === "not_confirmed") {
            this.notification.add(
                _t("Prescription %s is not confirmed yet.", result.name || code),
                { type: "warning" }
            );
        } else if (error === "already_dispensed") {
            this.notification.add(
                _t("Prescription %s has already been dispensed.", result.name || code),
                { type: "warning" }
            );
        } else {
            // Not a prescription (or unreadable): keep the default behaviour.
            this.barcodeReader?.showNotFoundNotification(parsed);
        }
        return false;
    },

    /** Open the preview popup (optionally pre-loaded with a result). */
    shaficOpenRxPopup(preset = {}) {
        this.dialog.add(RxScanPopup, {
            lookup: (code) => this.shaficLookupRx(code),
            confirm: (data) => this.shaficAddRxToOrder(data),
            data: preset.data || null,
            code: preset.code || "",
        });
    },

    /** Add the prescription's medicines to the current order, priced per
     *  dispensing unit, and tag the order so the prescription is marked
     *  dispensed when the order is paid. */
    async shaficAddRxToOrder(data) {
        const order = this.getOrder();
        if (!order || !data || !data.lines) {
            return;
        }
        for (const line of data.lines) {
            let product = this.models["product.product"].get(line.product_id);
            if (!product) {
                // Load the product on demand if it is not in the POS yet.
                try {
                    await this.data.read(
                        "product.product", [line.product_id]);
                    product =
                        this.models["product.product"].get(line.product_id);
                } catch (e) {
                    product = null;
                }
            }
            if (!product) {
                continue;
            }
            const orderline = await this.addLineToCurrentOrder(
                { product_id: product, qty: line.qty }, {});
            // Force the per-piece price so the total is correct regardless
            // of the product's stocking unit of measure.
            if (orderline && line.unit_price) {
                try {
                    orderline.setUnitPrice(line.unit_price);
                    orderline.price_type = "manual";
                } catch (e) {
                    // older signature fallback
                    orderline.price_unit = line.unit_price;
                }
            }
        }
        // Tag the order; pos.order.create marks the prescription dispensed.
        order.rx_prescription_ref = data.id;
    },
});
