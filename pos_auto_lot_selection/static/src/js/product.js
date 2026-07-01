/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { ComboConfiguratorPopup } from "@point_of_sale/app/components/popups/combo_configurator_popup/combo_configurator_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { computeComboItems } from "@point_of_sale/app/models/utils/compute_combo_items";

patch(PosStore.prototype, {

    _getOrderLotUsageForProduct(order, productId) {
        const usageList = [];
        for (const line of order.lines) {
            if (line.product_id?.id !== productId) continue;
        
            const lineQty = line.qty || 0;
            const packLots = line.pack_lot_ids || [];
            for (const pl of packLots) {
                const lot_name = pl.lot_name || pl.name || "";
                if (lot_name) {
                    usageList.push({
                        lot_name,
                        qty: lineQty || 1,
                    });
                }
            }
        }
        return usageList;
    },

    async _getLotAllocationPlan(product, totalQtyNeeded, locationIds, order) {

        const orderLotUsage = this._getOrderLotUsageForProduct(order, product.id);
        const availableLots = await this.env.services.orm.call(
            "stock.lot",
            "get_available_lots_for_pos",
            [],
            {
                product_id: product.id,
                location_ids: locationIds,
                order_lines: orderLotUsage,
            }
        );

        if (!availableLots || availableLots.length === 0) {
            return [];
        }

        const plan = [];
        let remaining = totalQtyNeeded;

        for (const lot of availableLots) {
            if (remaining <= 0) break;
            const allocate = Math.min(lot.qty, remaining);
            plan.push({ lot_name: lot.name, qty: allocate });
            remaining -= allocate;
        }

        return plan;
    },

    // MAIN OVERRIDE
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        let merge = true;
        order.assertEditable();

        const options = { ...opts };

        if ("price_unit" in vals) {
            merge = false;
        }

        if (typeof vals.product_tmpl_id === "number") {
            vals.product_tmpl_id = this.data.models["product.template"].get(vals.product_tmpl_id);
        }
        if (!vals.product_id && vals.product_tmpl_id) {
            vals.product_id = vals.product_tmpl_id.product_variant_ids[0];
        }
        if (typeof vals.product_id === "number") {
            vals.product_id = this.data.models["product.product"].get(vals.product_id);
        }
        const product = vals.product_id;

        const values = {
            price_type: "price_unit" in vals ? "manual" : "original",
            price_extra: 0,
            price_unit: 0,
            order_id: this.getOrder(),
            qty: 1,
            tax_ids: product.taxes_id.map((tax) => ["link", tax]),
            ...vals,
        };

        const selectedLocId = this.selected_stock_location_id
            ? [Number(this.selected_stock_location_id)]
            : (this.config?.stock_location_ids || []).map(
                (loc) => Number(loc.id ?? loc[0] ?? loc)
            );
        const getLocId = (loc) => Number(loc?.id ?? loc?.[0] ?? loc);

        let onhandQtyInLocation = 0;
        if (product.stock_quant_ids?.length) {
            for (const quant of product.stock_quant_ids) {
                const quantLocId = getLocId(quant.location_id);
                if (selectedLocId.includes(quantLocId)) {
                    onhandQtyInLocation += quant.quantity || 0;
                }
            }
        }
        if (product.point_of_sale_uom && onhandQtyInLocation < values.qty) {
            debugger
            let orderqty = values.qty;
            values.qty = onhandQtyInLocation;
            this.dialog.add(AlertDialog, {
                    title: _t("Insufficient Stock"),
                    body: `${product.display_name || product.name}

            ${_t("Available Quantity")}: ${onhandQtyInLocation}
            ${_t("Requested Quantity")}: ${orderqty}

            ${_t("The quantity has been adjusted to available stock.")}`,
                });
        }

        if (order.isSaleDisallowed(values, options)) {
            this.dialog.add(AlertDialog, {
                title: _t("Refund and Sales not allowed"),
                body: _t("It is not allowed to mix refunds and sales"),
            });
            return;
        }

        if (values.product_id.isConfigurable() && configure) {
            const payload = await this.openConfigurator(values.product_id, opts);
            if (payload) {
                const productFound = this.models["product.product"]
                    .filter((p) => p.raw?.product_template_variant_value_ids?.length > 0)
                    .find((p) =>
                        p.raw.product_template_variant_value_ids.every((v) =>
                            payload.attribute_value_ids.includes(v)
                        )
                    );
                Object.assign(values, {
                    attribute_value_ids: payload.attribute_value_ids
                        .filter((a) => {
                            if (productFound) {
                                const attr = this.data.models[
                                    "product.template.attribute.value"
                                ].get(a);
                                return (
                                    attr.is_custom ||
                                    attr.attribute_id.create_variant !== "always"
                                );
                            }
                            return true;
                        })
                        .map((id) => [
                            "link",
                            this.data.models["product.template.attribute.value"].get(id),
                        ]),
                    custom_attribute_value_ids: Object.entries(
                        payload.attribute_custom_values
                    ).map(([id, cus]) => [
                        "create",
                        {
                            custom_product_template_attribute_value_id:
                                this.data.models["product.template.attribute.value"].get(id),
                            custom_value: cus,
                        },
                    ]),
                    price_extra: values.price_extra + payload.price_extra,
                    qty: payload.qty || values.qty,
                    product_id: productFound || values.product_id,
                });
            } else {
                return;
            }
        } else if (values.product_id.product_template_variant_value_ids.length > 0) {
            const priceExtra = values.product_id.product_template_variant_value_ids
                .filter((attr) => attr.attribute_id.create_variant !== "always")
                .reduce((acc, attr) => acc + attr.price_extra, 0);
            values.price_extra += priceExtra;
        }

        if (values.product_id.isCombo() && configure) {
            const payload = await makeAwaitable(this.dialog, ComboConfiguratorPopup, {
                product: values.product_id,
            });
            if (!payload) return;

            const comboPrices = computeComboItems(
                values.product_id,
                payload,
                order.pricelist_id,
                this.data.models["decimal.precision"].getAll(),
                this.data.models["product.template.attribute.value"].getAllBy("id"),
                this.currency
            );

            values.combo_line_ids = comboPrices.map((comboItem) => [
                "create",
                {
                    product_id: comboItem.combo_item_id.product_id,
                    tax_ids: comboItem.combo_item_id.product_id.taxes_id.map((tax) => [
                        "link", tax,
                    ]),
                    combo_item_id: comboItem.combo_item_id,
                    price_unit: comboItem.price_unit,
                    price_type: "automatic",
                    order_id: order,
                    qty: 1,
                    attribute_value_ids: comboItem.attribute_value_ids?.map((attr) => [
                        "link", attr,
                    ]),
                    custom_attribute_value_ids: Object.entries(
                        comboItem.attribute_custom_values
                    ).map(([id, cus]) => [
                        "create",
                        {
                            custom_product_template_attribute_value_id:
                                this.data.models["product.template.attribute.value"].get(id),
                            custom_value: cus,
                        },
                    ]),
                },
            ]);
        }

        const code = opts.code;
        if (values.product_id.isTracked() && (configure || code)) {

            if (code && code.type === "lot") {
                const packLotLinesToEdit =
                    (!values.product_id.isAllowOnlyOneLot() &&
                        order
                            .getOrderlines()
                            .filter((line) => !line.getDiscount())
                            .find((line) => line.product_id.id === values.product_id.id)
                            ?.getPackLotLinesToEdit()) || [];

                const modifiedPackLotLines = Object.fromEntries(
                    packLotLinesToEdit.filter((item) => item.id).map((item) => [item.id, item.text])
                );
                const newPackLotLines = [{ lot_name: code.code }];
                values._pack_lot_ids = { modifiedPackLotLines, newPackLotLines };

            } else {
                const totalQty = values.qty || 1;
                const lotPlan = await this._getLotAllocationPlan(values.product_id, totalQty, selectedLocId, order);

                if (!lotPlan || lotPlan.length === 0) {
                    const line = this.data.models["pos.order.line"].create({
                        ...values,
                        qty: 0,
                        order_id: order,
                    });
                    line.setOptions(options);
                    this.selectOrderLine(order, line);
                    if (configure) this.numberBuffer.reset();
                    return line;
                }
                let lastLine = null;
                for (const allocation of lotPlan) {
                    const lineValues = {
                        ...values,
                        qty: allocation.qty,
                    };

                    // Resolve price for this qty
                    if (!lineValues.product_id.isCombo() && vals.price_unit === undefined) {
                        lineValues.price_unit = lineValues.product_id.getPrice(
                            order.pricelist_id,
                            lineValues.qty
                        );
                    }
                    if (lineValues.price_extra) {
                        lineValues.price_unit = lineValues.product_id.getPrice(
                            order.pricelist_id,
                            lineValues.qty,
                            lineValues.price_extra
                        );
                    }

                    const line = this.data.models["pos.order.line"].create({
                        ...lineValues,
                        order_id: order,
                    });
                    line.setOptions(options);
                    this.selectOrderLine(order, line);

                    line.setPackLotLines({
                        modifiedPackLotLines: {},
                        newPackLotLines: [{ lot_name: allocation.lot_name }],
                        setQuantity: true,
                    });

                    lastLine = line;
                }
                if (configure) this.numberBuffer.reset();

                this.hasJustAddedProduct = true;
                clearTimeout(this.productReminderTimeout);
                this.productReminderTimeout = setTimeout(() => {
                    this.hasJustAddedProduct = false;
                }, 3000);

                return lastLine;
            }
        }

        if (values.product_id.to_weight && this.config.iface_electronic_scale && configure) {
            if (values.product_id.isScaleAvailable) {
                const decimalAccuracy = this.models["decimal.precision"].find(
                    (dp) => dp.name === "Product Unit"
                ).digits;
                const overridedValues = {};
                if (order.pricelist_id) {
                    overridedValues.pricelist = order.pricelist_id;
                }
                if (order.fiscal_position_id) {
                    overridedValues.fiscalPosition = order.fiscal_position_id;
                }
                this.scale.setProduct(
                    values.product_id,
                    decimalAccuracy,
                    values.product_id.getTaxDetails({ overridedValues }).total_included
                );
                const weight = await this.weighProduct();
                if (weight) {
                    values.qty = weight;
                } else if (weight !== null) {
                    return;
                }
            } else {
                await values.product_id._onScaleNotAvailable();
            }
        }

        if (!values.product_id.isCombo() && vals.price_unit === undefined) {
            values.price_unit = values.product_id.getPrice(order.pricelist_id, values.qty);
        }
        const isScannedProduct = opts.code && opts.code.type === "product";
        if (values.price_extra && !isScannedProduct) {
            values.price_unit = values.product_id.getPrice(
                order.pricelist_id,
                values.qty,
                values.price_extra
            );
        }

        const line = this.data.models["pos.order.line"].create({
            ...values,
            order_id: order,
        });

        if (values.product_id.tracking === "lot") {
            const related_lines = [];
            const price = values.product_id.getPrice(
                order.pricelist_id,
                values.qty,
                values.price_extra,
                false,
                false,
                line,
                related_lines
            );
            related_lines.forEach((l) => l.setUnitPrice(price));
        }

        line.setOptions(options);
        this.selectOrderLine(order, line);
        if (configure) this.numberBuffer.reset();

        const selectedOrderline = order.getSelectedOrderline();
        if (options.draftPackLotLines && configure) {
            selectedOrderline.setPackLotLines({
                ...options.draftPackLotLines,
                setQuantity: options.quantity === undefined,
            });
        }

        let to_merge_orderline;
        let lineToReturn = line;
        for (const curLine of order.lines) {
            if (curLine.id !== line.id) {
                if (curLine.canBeMergedWith(line) && merge !== false) {
                    to_merge_orderline = curLine;
                }
            }
        }

        if (to_merge_orderline) {
            to_merge_orderline.merge(line);
            line.delete();
            lineToReturn = to_merge_orderline;
            this.selectOrderLine(order, to_merge_orderline);
        } else if (!selectedOrderline) {
            this.selectOrderLine(order, order.getLastOrderline());
        }

        if (product.isTracked() && values._pack_lot_ids) {
            this.selectedOrder.getSelectedOrderline()?.setPackLotLines({
                modifiedPackLotLines: values._pack_lot_ids.modifiedPackLotLines ?? {},
                newPackLotLines: values._pack_lot_ids.newPackLotLines ?? [],
                setQuantity: true,
            });
        }

        if (configure) this.numberBuffer.reset();

        this.hasJustAddedProduct = true;
        clearTimeout(this.productReminderTimeout);
        this.productReminderTimeout = setTimeout(() => {
            this.hasJustAddedProduct = false;
        }, 3000);

        return lineToReturn;
    },
});