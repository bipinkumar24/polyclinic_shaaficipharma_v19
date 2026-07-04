import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";
import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

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

        const currentPrescriptionOrigin = this.getOrder()
            .getOrderlines()
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
            this.getOrder().update({ fiscal_position_id: orderFiscalPos });
        }
        if (prescription_order.partner_id) {
            this.getOrder().setPartner(prescription_order.partner_id);
        }

        await this.settlePrescriptionSO(prescription_order, orderFiscalPos);
        this.selectOrderLine(this.getOrder(), this.getOrder().lines.at(-1));
    },

    async _getPrescriptionOrder(id) {
        return (await this.data.read("prescription.order", [id]))[0];
    },

    async settlePrescriptionSO(prescription_order, orderFiscalPos) {
        if (prescription_order.pricelist_id) {
            this.getOrder().set_pricelist(prescription_order.pricelist_id);
        }

        let previousProductLine = null;
        const order = this.getOrder();

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

            const newLineValues = {
                product_id: line.product_id,
                qty: line.product_uom_qty,
                price_unit: line.price_unit,
                discount: line.discount,
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
            };

            // Route through the SAME auto lot-assignment logic used for
            // manually-added products (pos_auto_lot_selection's addLineToOrder
            // override) instead of duplicating/reimplementing lot lookup here.
            // That override only runs its lot-allocation branch when
            // `configure` or `opts.code` is truthy (see
            // pos_auto_lot_selection/static/src/js/product.js); passing a
            // non-"lot"-typed code triggers the automatic multi-lot
            // allocation path (_getLotAllocationPlan) while configure stays
            // false, so this bulk/automated load never pops the product
            // configurator/combo/scale dialogs that `configure: true` would.
            // For a tracked product needing more quantity than one lot holds,
            // that path creates multiple order lines (one per lot) and
            // returns only the last one - so no further quantity/price
            // post-processing must run here, or it would clobber the split.
            const newLine = await this.addLineToCurrentOrder(
                newLineValues,
                { code: { type: "prescription_auto_lot" } },
                false
            );
            previousProductLine = newLine;

            this.selectOrderLine(order, newLine);
        }
    },
});