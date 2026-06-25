/** @odoo-module **/
import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class RxScanPopup extends Component {
    static template = "shafic_rx_worklist.RxScanPopup";
    static components = { Dialog };
    static props = {
        close: Function,
        lookup: Function,   // async (code) => result dict
        confirm: Function,  // (data) => void  (adds lines to the order)
        data: { type: [Object, { value: null }], optional: true },
        code: { type: String, optional: true },
    };

    setup() {
        this.state = useState({
            code: this.props.code || "",
            data: this.props.data || null,
            error: "",
            loading: false,
        });
        this.inputRef = useRef("codeInput");
        onMounted(() => {
            if (this.inputRef.el) {
                this.inputRef.el.focus();
            }
        });
    }

    async search() {
        const code = (this.state.code || "").trim();
        if (!code) {
            return;
        }
        this.state.loading = true;
        this.state.error = "";
        const result = await this.props.lookup(code);
        this.state.loading = false;
        if (!result || !result.found) {
            this.state.data = null;
            this.state.error = this._errorLabel(result);
            return;
        }
        this.state.data = result;
        this.state.error = "";
    }

    _errorLabel(result) {
        const err = result && result.error;
        if (err === "not_found") {
            return _t("No prescription found with that number.");
        }
        if (err === "not_confirmed") {
            return _t("That prescription has not been confirmed yet.");
        }
        if (err === "already_dispensed") {
            return _t("That prescription has already been dispensed.");
        }
        return _t("Could not read that code. Try again.");
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.search();
        }
    }

    get lines() {
        return (this.state.data && this.state.data.lines) || [];
    }

    addToOrder() {
        if (this.state.data && this.state.data.found) {
            this.props.confirm(this.state.data);
            this.props.close();
        }
    }
}
