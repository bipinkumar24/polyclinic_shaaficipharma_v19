/** @odoo-module **/

import { Component, useState, onWillStart, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const PAL = {
    ink: "#0B1F2A", inkSoft: "#13303d", surface: "#EEF2F1", card: "#FFFFFF",
    line: "#DCE5E4", teal: "#0E7C7B", good: "#1B9C6B", warn: "#C9842B",
    crit: "#C2453B", text: "#22343C", mute: "#6C7F87", faint: "#9DACB2",
};
const SERVICE_COLORS = ["#0E7C7B", "#2E86AB", "#C9842B", "#7A5BA8", "#1B9C6B",
                        "#C2453B", "#5B7186", "#B5651D"];

class ShaficPulse extends Component {
    setup() {
        this.PAL = PAL;
        this.orm = useService("orm");
        this.state = useState({ loading: true, scope: "all", view: "executive", data: null, open: null, error: null });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const method = this.state.view === "operations" ? "get_operations"
                : this.state.view === "physicians" ? "get_physicians" : "get_pulse";
            this.state.data = await this.orm.call("shafic.pulse.dashboard", method, [this.state.scope]);
            this.state.error = null;
        } catch (e) {
            this.state.error = (e && e.message) || "Could not load the pulse.";
        }
        this.state.loading = false;
    }

    setScope(key) {
        if (this.state.scope === key) return;
        this.state.scope = key;
        this.state.open = null;
        this.load();
    }

    toggle(key) { this.state.open = this.state.open === key ? null : key; }

    setView(v) {
        if (this.state.view === v) return;
        this.state.view = v;
        this.state.open = null;
        this.load();
    }
    tabStyle(v) {
        const on = this.state.view === v;
        return `padding:6px 14px;border-radius:8px;font-size:12.5px;font-weight:700;cursor:pointer;` +
               `border:1px solid ${on ? "transparent" : "#ffffff22"};` +
               `background:${on ? PAL.teal : "transparent"};color:${on ? "#ffffff" : "#9fc4c1"};`;
    }
    serviceColor(type) {
        const order = (this.state.data && this.state.data.service_order) || [];
        const i = order.indexOf(type);
        return SERVICE_COLORS[(i < 0 ? 0 : i) % SERVICE_COLORS.length];
    }

    // ---- presentation helpers ----
    toneColor(t) {
        return { good: PAL.good, warn: PAL.warn, crit: PAL.crit,
                 urgent: PAL.warn, watch: PAL.teal, mute: PAL.mute }[t] || PAL.good;
    }
    iconClass(name) {
        return { activity: "fa-heartbeat", users: "fa-users", clock: "fa-clock-o",
                 wallet: "fa-money", pill: "fa-medkit", shield: "fa-shield",
                 package: "fa-cubes" }[name] || "fa-circle";
    }
    deltaColor(d) {
        if (!d || d.dir === "flat") return PAL.mute;
        return d.good ? PAL.good : PAL.crit;
    }
    deltaArrow(d) {
        if (!d || d.dir === "flat") return "fa-minus";
        return d.dir === "up" ? "fa-caret-up" : "fa-caret-down";
    }
    cardStyle(tile) {
        return `background:${PAL.card};border:1px solid ${PAL.line};border-radius:14px;` +
               `overflow:hidden;display:flex;`;
    }
    barStyle(tile) {
        return `width:4px;flex:0 0 4px;background:${this.toneColor(tile.tone)};`;
    }
    badgeStyle(ready) {
        const c = ready ? PAL.good : PAL.warn;
        return `font-size:9.5px;font-weight:700;letter-spacing:.4px;padding:2px 6px;` +
               `border-radius:99px;color:${c};background:${c}1A;border:1px solid ${c}40;white-space:nowrap;`;
    }
    sparkGeom(series) {
        if (!series || series.length < 2) return null;
        const w = 96, h = 30;
        const min = Math.min(...series), max = Math.max(...series);
        const rng = (max - min) || 1;
        const pts = series.map((v, i) => {
            const x = (i / (series.length - 1)) * (w - 2) + 1;
            const y = h - 2 - ((v - min) / rng) * (h - 4);
            return [x, y];
        });
        const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
        const last = pts[pts.length - 1];
        return { line, area: `${line} L ${w - 1} ${h} L 1 ${h} Z`, cx: last[0].toFixed(1), cy: last[1].toFixed(1) };
    }
    scopeBtnStyle(key) {
        const on = this.state.scope === key;
        return `padding:6px 12px;border-radius:99px;font-size:12.5px;font-weight:600;cursor:pointer;` +
               `border:1px solid ${on ? "transparent" : "#ffffff33"};` +
               `background:${on ? "#ffffff" : "transparent"};color:${on ? PAL.ink : "#cfe0df"};`;
    }
    detailToneColor(t) { return this.toneColor(t); }

    static template = xml`
    <div t-att-style="'background:' + PAL.surface + ';min-height:100%;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:' + PAL.text + ';'">

        <!-- header -->
        <div t-att-style="'background:' + PAL.ink + ';color:#fff;padding:16px 18px 18px;'">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;">
                <div>
                    <div style="display:flex;align-items:center;gap:8px;">
                        <i class="fa fa-stethoscope" style="color:#7fd6cf;"/>
                        <span style="font-weight:700;font-size:16px;">Shafic Polyclinic</span>
                        <span t-att-style="'font-size:11px;font-weight:700;color:' + PAL.ink + ';background:#7fd6cf;padding:1px 7px;border-radius:99px;'">PULSE</span>
                    </div>
                    <div style="color:#9fc4c1;font-size:12.5px;margin-top:3px;" t-esc="state.data and state.data.as_of"/>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:11.5px;color:#9fc4c1;">Live · your data</span>
                    <i class="fa fa-refresh" style="color:#6f9794;cursor:pointer;" t-on-click="() => this.load()"/>
                </div>
            </div>
            <div t-if="state.view !== 'physicians'" style="display:flex;align-items:center;gap:8px;margin-top:12px;flex-wrap:wrap;">
                <i class="fa fa-building-o" style="color:#6f9794;"/>
                <t t-foreach="(state.data and state.data.branches) or []" t-as="b" t-key="b.key">
                    <button t-att-style="scopeBtnStyle(b.key)" t-on-click="() => this.setScope(b.key)" t-esc="b.name"/>
                </t>
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:10px;">
                <button t-att-style="tabStyle('executive')" t-on-click="() => this.setView('executive')">Executive</button>
                <button t-att-style="tabStyle('operations')" t-on-click="() => this.setView('operations')">Operations</button>
                <button t-att-style="tabStyle('physicians')" t-on-click="() => this.setView('physicians')">Physicians</button>
            </div>
        </div>

        <!-- triage strip -->
        <div t-if="state.data and state.view !== 'physicians'" t-att-style="'background:' + PAL.inkSoft + ';padding:10px 18px 14px;'">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <i class="fa fa-heartbeat" style="color:#7fd6cf;font-size:12px;"/>
                <span style="color:#cfe0df;font-size:11px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;">Needs attention now</span>
                <span style="color:#6f9794;font-size:11px;">· <t t-esc="state.data.triage.length"/> flags</span>
            </div>
            <div t-if="state.data.triage.length === 0" style="display:inline-flex;align-items:center;gap:8px;color:#7fd6cf;font-size:13px;font-weight:600;">
                <i class="fa fa-check-circle"/> All vitals stable
            </div>
            <div t-else="" style="display:flex;gap:8px;flex-wrap:wrap;">
                <t t-foreach="state.data.triage" t-as="t" t-key="t_index">
                    <span t-att-style="'background:#fff;border-left:3px solid ' + toneColor(t.tone) + ';border-radius:8px;padding:7px 11px;font-size:12.5px;font-weight:600;color:' + PAL.text + ';display:inline-flex;align-items:center;gap:8px;'">
                        <span t-att-style="'width:8px;height:8px;border-radius:99px;background:' + toneColor(t.tone) + ';display:inline-block;'"/>
                        <t t-esc="t.label"/>
                    </span>
                </t>
            </div>
        </div>

        <!-- loading / error -->
        <div t-if="state.loading" style="padding:40px;text-align:center;color:#6C7F87;">Loading the pulse…</div>
        <div t-if="state.error" style="padding:24px;color:#C2453B;font-weight:600;" t-esc="state.error"/>

        <!-- KPI grid -->
        <div t-if="state.data and !state.loading and state.view !== 'physicians'" style="display:grid;gap:12px;padding:16px;grid-template-columns:repeat(auto-fill,minmax(248px,1fr));">
            <t t-foreach="state.data.tiles" t-as="tile" t-key="tile.key">
                <div t-att-style="cardStyle(tile)">
                    <div t-att-style="barStyle(tile)"/>
                    <div style="padding:14px 16px;flex:1;min-width:0;">

                        <!-- eyebrow -->
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;">
                            <span t-att-style="'color:' + PAL.mute + ';font-size:11.5px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;display:inline-flex;align-items:center;gap:6px;'">
                                <i t-att-class="'fa ' + iconClass(tile.icon)" t-att-style="'color:' + PAL.teal + ';'"/>
                                <t t-esc="tile.label"/>
                            </span>
                            <span t-att-style="badgeStyle(tile.ready)" t-esc="tile.ready ? 'LIVE' : 'NEEDS SOURCE'"/>
                        </div>

                        <!-- value row -->
                        <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:8px;">
                            <div style="min-width:0;">
                                <div style="display:flex;align-items:flex-end;gap:6px;line-height:1;">
                                    <span t-att-style="'font-family:ui-monospace,Menlo,monospace;font-size:30px;font-weight:700;letter-spacing:-.5px;color:' + PAL.ink + ';'" t-esc="tile.value"/>
                                    <span t-if="tile.sub" t-att-style="'color:' + PAL.mute + ';font-size:13px;font-weight:600;padding-bottom:2px;'" t-esc="tile.sub"/>
                                </div>
                                <div t-if="tile.note" t-att-style="'color:' + PAL.faint + ';font-size:11.5px;margin-top:5px;'" t-esc="tile.note"/>
                            </div>
                            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
                                <span t-if="tile.extra" t-att-style="'color:' + PAL.warn + ';font-size:12px;font-weight:700;'" t-esc="tile.extra"/>
                                <t t-set="g" t-value="sparkGeom(tile.series)"/>
                                <svg t-if="g" width="96" height="30" style="display:block;">
                                    <path t-att-d="g.area" t-att-fill="toneColor(tile.tone)" fill-opacity="0.08"/>
                                    <path t-att-d="g.line" fill="none" t-att-stroke="toneColor(tile.tone)" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>
                                    <circle t-att-cx="g.cx" t-att-cy="g.cy" r="2.1" t-att-fill="toneColor(tile.tone)"/>
                                </svg>
                            </div>
                        </div>

                        <!-- deltas -->
                        <div t-if="tile.delta_yest or tile.delta_week" style="display:flex;gap:14px;margin-top:10px;">
                            <span t-if="tile.delta_yest" t-att-style="'display:inline-flex;align-items:center;gap:3px;font-size:11.5px;font-weight:600;color:' + deltaColor(tile.delta_yest) + ';'">
                                <i t-att-class="'fa ' + deltaArrow(tile.delta_yest)"/><t t-esc="tile.delta_yest.pct"/>% <span t-att-style="'color:' + PAL.faint + ';font-weight:500;'">vs yest</span>
                            </span>
                            <span t-if="tile.delta_week" t-att-style="'display:inline-flex;align-items:center;gap:3px;font-size:11.5px;font-weight:600;color:' + deltaColor(tile.delta_week) + ';'">
                                <i t-att-class="'fa ' + deltaArrow(tile.delta_week)"/><t t-esc="tile.delta_week.pct"/>% <span t-att-style="'color:' + PAL.faint + ';font-weight:500;'">vs last wk</span>
                            </span>
                        </div>

                        <!-- hint -->
                        <div t-if="tile.hint" t-att-style="'color:' + PAL.faint + ';font-size:11px;margin-top:8px;font-style:italic;'" t-esc="tile.hint"/>

                        <!-- expandable details -->
                        <t t-if="tile.details and tile.details.length">
                            <button t-att-style="'margin-top:10px;font-size:11.5px;font-weight:600;color:' + PAL.teal + ';cursor:pointer;background:none;border:none;padding:0;display:inline-flex;align-items:center;gap:4px;'" t-on-click="() => this.toggle(tile.key)">
                                <t t-esc="tile.details_label or 'view'"/>
                                <i t-att-class="state.open === tile.key ? 'fa fa-chevron-up' : 'fa fa-chevron-down'"/>
                            </button>
                            <div t-if="state.open === tile.key" t-att-style="'margin-top:8px;border-top:1px solid ' + PAL.line + ';padding-top:8px;'">
                                <t t-foreach="tile.details" t-as="row" t-key="row_index">
                                    <div style="display:flex;align-items:center;justify-content:space-between;font-size:12px;padding:3px 0;gap:10px;">
                                        <span t-att-style="'color:' + PAL.text + ';'" t-esc="row.left"/>
                                        <span t-att-style="'font-weight:600;white-space:nowrap;color:' + detailToneColor(row.tone) + ';'" t-esc="row.right"/>
                                    </div>
                                </t>
                            </div>
                        </t>
                    </div>
                </div>
            </t>
        </div>

        <!-- physician scorecard -->
        <div t-if="state.data and !state.loading and state.view === 'physicians'" style="padding:16px;">
            <div t-if="state.data.message" t-att-style="'background:#fff;border:1px solid ' + PAL.line + ';border-radius:12px;padding:16px;color:' + PAL.warn + ';font-weight:600;'" t-esc="state.data.message"/>
            <t t-else="">
                <div t-att-style="'background:' + PAL.ink + ';color:#fff;border-radius:12px;padding:14px 16px;margin-bottom:14px;'">
                    <div style="font-size:12px;color:#9fc4c1;">Physician scorecard · <t t-esc="state.data.period"/> · all branches</div>
                    <div style="display:flex;gap:22px;flex-wrap:wrap;margin-top:8px;">
                        <div>
                            <div style="font-family:ui-monospace,Menlo,monospace;font-size:23px;font-weight:700;" t-esc="state.data.total_revenue_str"/>
                            <div style="font-size:11px;color:#9fc4c1;">total revenue</div>
                        </div>
                        <div>
                            <div style="font-family:ui-monospace,Menlo,monospace;font-size:23px;font-weight:700;" t-esc="state.data.total_rx"/>
                            <div style="font-size:11px;color:#9fc4c1;">prescriptions</div>
                        </div>
                        <div>
                            <div style="font-family:ui-monospace,Menlo,monospace;font-size:23px;font-weight:700;" t-esc="state.data.total_rx_value_str"/>
                            <div style="font-size:11px;color:#9fc4c1;">Rx value</div>
                        </div>
                        <div>
                            <div style="font-family:ui-monospace,Menlo,monospace;font-size:23px;font-weight:700;color:#7fd6cf;" t-esc="state.data.total_capture_str"/>
                            <div style="font-size:11px;color:#9fc4c1;">script capture</div>
                        </div>
                    </div>
                </div>
                <t t-foreach="state.data.physicians" t-as="ph" t-key="ph.key">
                    <div t-att-style="'background:#fff;border:1px solid ' + PAL.line + ';border-left:4px solid ' + (ph.unassigned ? PAL.warn : PAL.teal) + ';border-radius:14px;padding:14px 16px;margin-bottom:12px;'">
                        <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
                            <div style="display:flex;align-items:center;gap:10px;min-width:0;">
                                <span t-if="!ph.unassigned" t-att-style="'flex:0 0 auto;width:26px;height:26px;border-radius:99px;background:' + PAL.ink + ';color:#fff;font-weight:700;font-size:13px;display:flex;align-items:center;justify-content:center;'" t-esc="ph.rank"/>
                                <span t-if="ph.unassigned" t-att-style="'flex:0 0 auto;width:26px;height:26px;border-radius:99px;background:' + PAL.warn + ';color:#fff;display:flex;align-items:center;justify-content:center;'"><i class="fa fa-exclamation"/></span>
                                <span t-att-style="'font-weight:700;font-size:15px;color:' + PAL.text + ';overflow:hidden;text-overflow:ellipsis;'" t-esc="ph.name"/>
                            </div>
                            <div style="text-align:right;flex:0 0 auto;">
                                <div t-att-style="'font-family:ui-monospace,Menlo,monospace;font-size:21px;font-weight:700;color:' + PAL.ink + ';'" t-esc="ph.revenue_str"/>
                                <div t-att-style="'font-size:11px;color:' + PAL.faint + ';'"><t t-esc="ph.share_pct"/>% of clinic</div>
                            </div>
                        </div>
                        <div t-att-style="'display:flex;height:8px;border-radius:6px;overflow:hidden;margin-top:12px;background:' + PAL.surface + ';'">
                            <t t-foreach="ph.mix" t-as="seg" t-key="seg.type">
                                <div t-att-style="'width:' + seg.pct + '%;background:' + serviceColor(seg.type) + ';'" t-att-title="seg.type"/>
                            </t>
                        </div>
                        <div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:8px;">
                            <t t-foreach="ph.mix" t-as="seg" t-key="seg.type">
                                <span t-att-style="'display:inline-flex;align-items:center;gap:5px;font-size:11.5px;color:' + PAL.text + ';'">
                                    <span t-att-style="'width:8px;height:8px;border-radius:2px;background:' + serviceColor(seg.type) + ';display:inline-block;'"/>
                                    <t t-esc="seg.type"/> <span t-att-style="'color:' + PAL.faint + ';'"><t t-esc="seg.revenue_str"/></span>
                                </span>
                            </t>
                        </div>
                        <div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:10px;font-size:12px;">
                            <span t-att-style="'color:' + PAL.text + ';'"><b t-esc="ph.patients"/> patients</span>
                            <span t-att-style="'color:' + PAL.teal + ';font-weight:600;'"><b t-esc="ph.rx_count"/> scripts · <t t-esc="ph.rx_value_str"/></span>
                            <span t-att-style="'color:' + PAL.good + ';font-weight:600;'">Capture <t t-esc="ph.capture_str"/></span>
                            <span t-att-style="'color:' + PAL.good + ';'">Paid <t t-esc="ph.paid_str"/></span>
                            <span t-att-style="'color:' + PAL.warn + ';'">Outstanding <t t-esc="ph.outstanding_str"/></span>
                            <span t-att-style="'color:' + PAL.faint + ';'"><t t-esc="ph.lines"/> lines</span>
                        </div>
                        <div t-if="ph.unassigned" t-att-style="'margin-top:8px;font-size:11px;color:' + PAL.warn + ';font-style:italic;'">No ordering physician captured on these invoices.</div>
                    </div>
                </t>
                <div t-att-style="'font-size:11.5px;color:' + PAL.mute + ';margin-top:4px;line-height:1.5;'">“Unassigned” is revenue on invoices with no physician — mostly lab/radiology orders where the ordering doctor isn’t stamped on the invoice yet. Wiring the lab/radiology ordering physician moves this onto the right doctor.</div>
            </t>
        </div>

        <!-- sources -->
        <div t-if="state.data and !state.loading and state.view !== 'physicians'" style="padding:0 16px 28px;">
            <div t-att-style="'background:' + PAL.card + ';border:1px solid ' + PAL.line + ';border-radius:12px;padding:12px 16px;'">
                <div t-att-style="'display:flex;align-items:center;gap:8px;font-size:12.5px;font-weight:700;color:' + PAL.ink + ';'">
                    <i class="fa fa-info-circle" t-att-style="'color:' + PAL.teal + ';'"/> Data sources
                </div>
                <t t-foreach="state.data.sources" t-as="s" t-key="s_index">
                    <div t-att-style="'display:flex;gap:10px;padding:5px 0;font-size:12px;' + (s_index > 0 ? 'border-top:1px solid ' + PAL.line + ';' : '')">
                        <span t-att-style="'min-width:120px;font-weight:700;color:' + PAL.ink + ';'" t-esc="s.name"/>
                        <span t-att-style="'min-width:92px;font-size:10px;font-weight:700;color:' + (s.status === 'live' ? PAL.good : (s.status === 'error' ? PAL.crit : PAL.warn)) + ';'" t-esc="s.status.toUpperCase()"/>
                        <span t-att-style="'color:' + PAL.mute + ';'" t-esc="s.detail"/>
                    </div>
                </t>
            </div>
        </div>
    </div>`;
}

registry.category("actions").add("shafic_pulse_dashboard", ShaficPulse);
