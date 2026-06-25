/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

/**
 * Shafic Pharmacy Data Completeness Dashboard
 *
 * Visualises the same data-completeness rules used by the bonus
 * scorecard, and provides a drill-down into the products that are
 * actually missing fields.
 */
export class PharmacyDataCompleteness extends Component {
    static template = "shafic_pharmacy_reports.PharmacyDataCompleteness";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: {
                total: 0, complete: 0, incomplete: 0, pct_complete: 0,
                missing_barcode: 0, missing_ref: 0, missing_lot: 0,
                by_category: [],
            },
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call(
            "report.pharmacy.data.completeness",
            "get_completeness_summary",
            [false]
        );
        this.state.loading = false;
    }

    /** Open the drill-down list of incomplete products. */
    openIncomplete() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Incomplete Products",
            res_model: "report.pharmacy.data.completeness",
            view_mode: "list",
            views: [[false, "list"]],
            domain: [["is_complete", "=", false]],
        });
    }

    openMissingField(field) {
        const labels = {
            missing_barcode: "Products Missing Barcode",
            missing_ref: "Products Missing Internal Reference",
            missing_lot: "Products Missing Lot/Batch",
        };
        this.action.doAction({
            type: "ir.actions.act_window",
            name: labels[field] || "Incomplete Products",
            res_model: "report.pharmacy.data.completeness",
            view_mode: "list",
            views: [[false, "list"]],
            domain: [[field, "=", true]],
        });
    }

    openCategory(categoryKey) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Incomplete Products in Category",
            res_model: "report.pharmacy.data.completeness",
            view_mode: "list",
            views: [[false, "list"]],
            domain: [
                ["pharmacy_category", "=", categoryKey],
                ["is_complete", "=", false],
            ],
        });
    }

    pctClass(pct) {
        if (pct >= 98) return "text-success";
        if (pct >= 90) return "text-warning";
        return "text-danger";
    }

    barWidth(pct) {
        return `${Math.max(2, Math.min(100, pct))}%`;
    }

    barClass(pct) {
        if (pct >= 98) return "bg-success";
        if (pct >= 90) return "bg-warning";
        return "bg-danger";
    }
}

registry.category("actions").add(
    "shafic_pharmacy_data_completeness", PharmacyDataCompleteness
);
