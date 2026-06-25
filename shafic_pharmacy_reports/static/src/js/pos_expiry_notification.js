/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Popup shown to the POS cashier when a scanned product has multiple
 * lots with different expiration dates. Read-only — the cashier just
 * acknowledges. Lot selection itself is still automatic FEFO.
 *
 * Props (passed in by the caller via the dialog service):
 *   productName: string — what's shown in the dialog title
 *   lots: array of { lot_name, expiration_date, days_to_expiry, qty }
 *         already sorted by expiration ascending (FEFO order)
 *   close: () => void — auto-injected by Dialog service
 */
export class ExpiryNotificationPopup extends Component {
    static template = "shafic_pharmacy_reports.ExpiryNotificationPopup";
    static components = { Dialog };
    static props = {
        productName: { type: String },
        lots: { type: Array },
        close: { type: Function, optional: true },
    };

    /** Treat lots within this many days as urgent — gets red badge.
     * Mirrors the backend expiry_alert_days but kept simple here:
     * the row-level styling decision doesn't need to round-trip. */
    isUrgent(lot) {
        return lot.days_to_expiry !== null && lot.days_to_expiry <= 30;
    }

    /** Formatted "in X days" / "Y days ago" / "today" label. */
    daysLabel(lot) {
        const d = lot.days_to_expiry;
        if (d === null || d === undefined) return "";
        if (d === 0) return "today";
        if (d < 0) return `expired ${Math.abs(d)} days ago`;
        return `in ${d} days`;
    }

    acknowledge() {
        this.props.close?.();
    }
}
