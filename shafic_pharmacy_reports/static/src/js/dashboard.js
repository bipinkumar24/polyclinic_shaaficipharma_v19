/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

/**
 * Shafic Pharmacy Executive Dashboard
 * Renders real-time KPI widgets for pharmacy POS operations.
 */
export class PharmacyDashboard extends Component {
    static template = "shafic_pharmacy_reports.PharmacyDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            branchId: false,
            branches: [],
            data: {},
        });

        onWillStart(async () => {
            await this.loadBranches();
            await this.loadData();
        });
    }

    async loadBranches() {
        this.state.branches = await this.orm.call(
            "pharmacy.dashboard", "get_branches", []
        );
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call(
            "pharmacy.dashboard", "get_dashboard_data",
            [this.state.branchId || false]
        );
        this.state.loading = false;
    }

    async onBranchChange(ev) {
        const value = ev.target.value;
        this.state.branchId = value ? parseInt(value, 10) : false;
        await this.loadData();
    }

    formatCurrency(value) {
        const symbol = this.state.data.currency_symbol || "";
        const num = (value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return `${symbol} ${num}`;
    }

    formatPercent(value) {
        return `${(value || 0).toFixed(1)}%`;
    }

    /** Open a backend action by xml id for drill-down. */
    openAction(xmlId) {
        this.action.doAction(xmlId);
    }

    /** Open Stock Movement Analysis pre-filtered to dead-both (worst case). */
    openDeadStock() {
        this.action.doAction(
            "shafic_pharmacy_reports.action_report_stock_movement",
            {
                additionalContext: {
                    search_default_both_dead: 1,
                },
            }
        );
    }

    /** Open the Profitability report so the user can break the gross
     * profit number down by product. Defaults to this month, grouped by
     * product, worst margin surfaced via the report's own ordering. */
    openProfitability() {
        this.action.doAction(
            "shafic_pharmacy_reports.action_report_profitability",
            {
                additionalContext: {
                    search_default_this_month: 1,
                    search_default_group_product: 1,
                },
            }
        );
    }

    /** Maximum value in the 7-day trend, used to scale the bar heights. */
    get trendMax() {
        const trend = this.state.data.sales_trend || [];
        return Math.max(1, ...trend.map((d) => d.value));
    }

    barHeight(value) {
        return `${Math.max(2, (value / this.trendMax) * 100)}%`;
    }
}

registry.category("actions").add(
    "shafic_pharmacy_dashboard", PharmacyDashboard
);
