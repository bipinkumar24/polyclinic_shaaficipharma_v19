import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {

    async onClickPrescriptionOrder(clickedOrderId) {
        const selectedOption = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("What do you want to do?"),
            list: [
                { id: "0", label: _t("Settle the order"), item: "settle" },
            ],
        });
        if (!selectedOption) return;

        const prescription_order = await this._getPrescriptionOrder(clickedOrderId);

        const currentPrescriptionOrigin = this.get_order()
            .get_orderlines()
            .find((line) => line.prescription_order_origin_id)?.prescription_order_origin_id;

        if (currentPrescriptionOrigin?.id) {
            const linkedSO = await this._getPrescriptionOrder(currentPrescriptionOrigin.id);
            if (
                linkedSO.partner_id?.id !== prescription_order.partner_id?.id ||
                linkedSO.partner_invoice_id?.id !== prescription_order.partner_invoice_id?.id ||
                linkedSO.partner_shipping_id?.id !== prescription_order.partner_shipping_id?.id
            ) {
                this.add_new_order({ partner_id: prescription_order.partner_id });
                this.notification.add(_t("A new order has been created."));
            }
        }

        const orderFiscalPos =
            prescription_order.fiscal_position_id &&
            this.models["account.fiscal.position"].find(
                (p) => p.id === prescription_order.fiscal_position_id
            );

        if (orderFiscalPos) {
            this.get_order().update({ fiscal_position_id: orderFiscalPos });
        }
        if (prescription_order.partner_id) {
            this.get_order().set_partner(prescription_order.partner_id);
        }

        await this.settlePrescriptionSO(prescription_order, orderFiscalPos);
        this.selectOrderLine(this.get_order(), this.get_order().lines.at(-1));
    },

    async _getPrescriptionOrder(id) {
        return (await this.data.read("prescription.order", [id]))[0];
    },

    async settlePrescriptionSO(prescription_order, orderFiscalPos) {
        if (prescription_order.pricelist_id) {
            this.get_order().set_pricelist(prescription_order.pricelist_id);
        }

        let previousProductLine = null;
        const order = this.get_order();

        for (const line of prescription_order.prescription_line_ids) {

            if (line.display_type === "line_note") {
                if (previousProductLine) {
                    const prev = previousProductLine.customer_note;
                    previousProductLine.customer_note = prev
                        ? prev + "--" + line.name
                        : line.name;
                }
                continue;
            }

            if (line.display_type === "line_section") {
                continue;
            }

            let pack_lot_ids = [];

            // if (line.product_id.isTracked()) {
            //     try {
            //         const result = await this.env.services.orm.call(
            //             "stock.lot",
            //             "get_available_lots_for_pos",
            //             [],
            //             { product_id: line.product_id.id }
            //         );
            //         // Normalize: handle both string[] and {name}[] from server
            //         const lotNames = (result[0] || [])
            //             .map((item) =>
            //                 typeof item === "string"
            //                     ? item
            //                     : (item?.name || item?.lot_name || "")
            //             )
            //             .filter(Boolean);

            //         // Odoo 18 ORM format to create related records inline:
            //         // ["create", { field: value }]
            //         pack_lot_ids = lotNames.map((lotName) => [
            //             "create",
            //             { lot_name: lotName },
            //         ]);

            //     } catch (err) {
            //         console.error("[Prescription] lot fetch failed:", err);
            //         pack_lot_ids = [];
            //     }

            //     // Fallback: if server returned nothing, use lots from the
            //     // prescription order line itself
            //     if (pack_lot_ids.length === 0 && line.pack_lot_ids?.length > 0) {
            //         const lotNames = line.lot_names || [];
            //         pack_lot_ids = lotNames.map((name) => [
            //             "create",
            //             { lot_name: name },
            //         ]);
            //     }

            //     if (pack_lot_ids.length === 0) {
            //         console.warn(
            //             "[Prescription] No lots found for:",
            //             line.product_id.display_name,
            //             "id:", line.product_id.id
            //         );
            //     }
            // }
            if (line.product_id.isTracked()) {
                try {
                    const result = await this.env.services.orm.call(
                        "stock.lot",
                        "get_available_lots_for_pos",
                        [],
                        { product_id: line.product_id.id }
                    );
                    const requiredQty = line.product_uom_qty;
                    const totalAvailableQty = (result || []).reduce(
                        (sum, lot) => sum + (lot.qty || 0),
                        0
                    );
                    let remainingQty = requiredQty;
                    pack_lot_ids = [];

                    for (const lot of result) {
                        if (remainingQty <= 0) break;

                        const useQty = Math.min(remainingQty, lot.qty);
                        pack_lot_ids.push([
                            "create",
                            {
                                lot_name: lot.lot_name || lot.name,
                                qty: useQty,
                            },
                        ]);
                        // for (let i = 0; i < useQty; i++) {
                        //     pack_lot_ids.push([
                        //         "create",
                        //         { lot_name: lot.lot_name || lot.name },
                        //     ]);
                        // }

                        remainingQty -= useQty;
                    }

                } catch (err) {
                    console.error("[Prescription] lot fetch failed:", err);
                    pack_lot_ids = [];
                }
            }

            const newLineValues = {
                product_id: line.product_id,
                qty: line.product_uom_qty,
                price_unit: line.price_unit,
                price_type: "automatic",
                custom_uom_id: line.product_uom?.name,
                custom_uom_number_id: line.product_uom.id,
                tax_ids:
                    orderFiscalPos || !line.tax_ids
                        ? undefined
                        : line.tax_ids.map((t) => ["link", t]),
                prescription_order_origin_id: prescription_order,
                prescription_order_line_id: line,
                customer_note: line.customer_note,
                description: line.name,
                order_id: order,
                pack_lot_ids: pack_lot_ids,
            };

            console.log("[Prescription] newLineValues with lots:", newLineValues);
            const newLine = await this.addLineToCurrentOrder(newLineValues, {}, false);
            previousProductLine = newLine;

            this.selectOrderLine(order, newLine);

            newLine.setQuantityFromPOL(line);
            newLine.set_unit_price(line.price_unit);
            newLine.set_discount(line.discount);
            // order.recomputeOrderData();

            // Always keep a single order line carrying the full quantity.
            // (Previously, products whose UoM is not pos-groupable were split
            // into one line per unit, e.g. qty 3 -> 3 lines of qty 1.)
        }
    },
});