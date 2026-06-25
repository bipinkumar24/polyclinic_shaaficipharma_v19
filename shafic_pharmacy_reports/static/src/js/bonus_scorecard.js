/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

/**
 * Shafic Pharmacy Inventory Bonus Scorecard
 * Shows the three bonus KPIs, their scores against target, and the
 * dollar payout earned for the selected month.
 */
export class PharmacyBonusScorecard extends Component {
    static template = "shafic_pharmacy_reports.PharmacyBonusScorecard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        const now = new Date();
        this.state = useState({
            loading: true,
            year: now.getFullYear(),
            month: now.getMonth() + 1,
            data: {},
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call(
            "pharmacy.bonus.scorecard", "get_scorecard",
            [this.state.year, this.state.month, false]
        );
        this.state.loading = false;
    }

    async onMonthChange(ev) {
        const [y, m] = ev.target.value.split("-");
        this.state.year = parseInt(y, 10);
        this.state.month = parseInt(m, 10);
        await this.loadData();
    }

    async captureMonth() {
        await this.orm.call(
            "pharmacy.bonus.scorecard", "capture_month_snapshot",
            [this.state.year, this.state.month, false, true]
        );
        await this.loadData();
    }

    get isCurrentMonth() {
        const now = new Date();
        return this.state.year === now.getFullYear()
            && this.state.month === now.getMonth() + 1;
    }

    get sourceLabel() {
        const src = this.state.data.source;
        if (src === "snapshot") {
            return "Snapshot of month-end figures";
        }
        if (src === "missing") {
            return "No snapshot captured for this month";
        }
        return "Live figures from current inventory";
    }

    get sourceClass() {
        const src = this.state.data.source;
        if (src === "snapshot") return "badge text-bg-info";
        if (src === "missing") return "badge text-bg-secondary";
        return "badge text-bg-success";
    }

    get monthValue() {
        const m = String(this.state.month).padStart(2, "0");
        return `${this.state.year}-${m}`;
    }

    money(value) {
        const num = (value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return `$ ${num}`;
    }

    scoreClass(score) {
        if (score >= 80) {
            return "text-success";
        }
        if (score >= 40) {
            return "text-warning";
        }
        return "text-danger";
    }
}

registry.category("actions").add(
    "shafic_pharmacy_bonus_scorecard", PharmacyBonusScorecard
);
