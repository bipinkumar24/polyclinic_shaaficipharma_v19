# -*- coding: utf-8 -*-
"""Shafic CEO Pulse — backend aggregation.

Design rules:
* Every tile is computed inside its own guard (_safe). A tile that cannot
  find its data source returns a clean ``needs_source``/``error`` status and
  NEVER raises, so the dashboard always loads.
* All numeric work and formatting is done here in Python; the OWL frontend is
  a thin renderer that just displays what this method returns.
* Nothing is hard-coded to a field we have not confirmed. Optional models and
  fields (branch, POS, appointments, prescriptions) are feature-detected at
  runtime via ``in self.env`` / ``in Model._fields``.
"""

import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

PERIOD_DAYS = 90  # window used to rank A-class (top selling) products


class ShaficPulseDashboard(models.TransientModel):
    _name = "shafic.pulse.dashboard"
    _description = "Shafic CEO Pulse — KPI aggregation endpoint"

    # ------------------------------------------------------------------ #
    # formatting helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _money(n):
        try:
            n = float(n or 0.0)
        except (TypeError, ValueError):
            return "—"
        frac = abs(n - int(n)) > 1e-9
        s = "{:,.2f}".format(abs(n)) if frac else "{:,.0f}".format(abs(n))
        return ("-$" if n < 0 else "$") + s

    @staticmethod
    def _pct(n):
        try:
            n = float(n or 0.0)
        except (TypeError, ValueError):
            return "—"
        return ("{:.1f}%".format(n)) if abs(n - round(n)) > 1e-9 else ("{:.0f}%".format(n))

    @staticmethod
    def _delta(now, past, good_up=True):
        try:
            now = float(now)
            past = float(past)
        except (TypeError, ValueError):
            return False
        if not past:
            return False
        change = (now - past) / abs(past) * 100.0
        flat = abs(change) < 0.5
        return {
            "pct": round(abs(change), 1),
            "dir": "flat" if flat else ("up" if change > 0 else "down"),
            "good": None if flat else ((change > 0) == good_up),
        }

    # ------------------------------------------------------------------ #
    # date / branch utilities
    # ------------------------------------------------------------------ #
    def _tz(self):
        return pytz.timezone(self.env.user.tz or "UTC")

    def _day_bounds(self, day):
        """Return (start, end) naive UTC datetimes for a local calendar day."""
        tz = self._tz()
        start_local = tz.localize(datetime.combine(day, time.min))
        end_local = tz.localize(datetime.combine(day, time.max))
        to_utc = lambda d: d.astimezone(pytz.UTC).replace(tzinfo=None)
        return to_utc(start_local), to_utc(end_local)

    def _branch_field(self, model_name="account.move"):
        Model = self.env.get(model_name)
        if Model is not None and "branch_id" in Model._fields:
            return "branch_id"
        return None

    def _branches(self):
        """Dynamically discover branches; empty list = single-scope clinic."""
        bf = self._branch_field()
        if not bf:
            return []
        comodel = self.env["account.move"]._fields["branch_id"].comodel_name
        try:
            recs = self.env[comodel].search([], limit=20)
            return [{"key": str(r.id), "name": r.display_name} for r in recs]
        except Exception:  # noqa: BLE001
            return []

    def _branch_domain(self, scope, model_name="account.move"):
        bf = self._branch_field(model_name)
        if bf and scope not in (None, "all", "", "0"):
            try:
                return [(bf, "=", int(scope))]
            except (TypeError, ValueError):
                return []
        return []

    # ------------------------------------------------------------------ #
    # revenue + COGS over a calendar day (clinic invoices + pharmacy POS)
    # ------------------------------------------------------------------ #
    def _invoice_rev_cogs(self, day, scope):
        AML = self.env["account.move.line"]
        dom = [
            ("parent_state", "=", "posted"),
            ("move_id.move_type", "=", "out_invoice"),
            ("date", "=", day),
            ("display_type", "=", "product"),
            ("product_id", "!=", False),
        ] + self._branch_domain(scope)
        rev = cogs = 0.0
        for ln in AML.search(dom):
            rev += ln.price_subtotal
            prod = ln.product_id
            if prod and prod.type in ("product", "consu"):
                cogs += abs(ln.quantity) * (prod.standard_price or 0.0)
        return rev, cogs

    def _pos_rev_cogs(self, day, scope):
        if "pos.order.line" not in self.env:
            return 0.0, 0.0
        start, end = self._day_bounds(day)
        dom = [
            ("order_id.date_order", ">=", fields.Datetime.to_string(start)),
            ("order_id.date_order", "<=", fields.Datetime.to_string(end)),
            ("order_id.state", "in", ["paid", "done", "invoiced"]),
        ] + self._branch_domain(scope, "pos.order.line")
        rev = cogs = 0.0
        for ln in self.env["pos.order.line"].search(dom):
            rev += ln.price_subtotal
            prod = ln.product_id
            if prod and prod.type in ("product", "consu"):
                cogs += abs(ln.qty) * (prod.standard_price or 0.0)
        return rev, cogs

    def _rev_cogs(self, day, scope):
        ir, ic = self._invoice_rev_cogs(day, scope)
        pr, pc = self._pos_rev_cogs(day, scope)
        return ir + pr, ic + pc

    def _daily_revenue_series(self, scope, days=14):
        """Cheap 14-day revenue trend (invoice + POS) for sparklines."""
        today = fields.Date.context_today(self)
        series = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            rev, _ = self._rev_cogs(d, scope)
            series.append(round(rev, 2))
        return series

    # ------------------------------------------------------------------ #
    # individual tiles — each returns a fully-formed tile dict
    # ------------------------------------------------------------------ #
    def _tile_margin(self, scope):
        today = fields.Date.context_today(self)
        rev_t, cogs_t = self._rev_cogs(today, scope)
        margin_t = rev_t - cogs_t
        m_yest = (lambda r, c: r - c)(*self._rev_cogs(today - timedelta(days=1), scope))
        m_week = (lambda r, c: r - c)(*self._rev_cogs(today - timedelta(days=7), scope))
        rev_series = self._daily_revenue_series(scope)
        ratio = (margin_t / rev_t) if rev_t else 0.0
        margin_series = [round(v * ratio, 2) for v in rev_series]  # trend approximation
        pct = (margin_t / rev_t * 100.0) if rev_t else 0.0
        return {
            "key": "margin", "label": "Gross margin · today", "icon": "activity",
            "value": self._money(margin_t), "sub": self._pct(pct),
            "note": "on %s revenue" % self._money(rev_t),
            "series": margin_series,
            "delta_yest": self._delta(margin_t, m_yest),
            "delta_week": self._delta(margin_t, m_week),
            "tone": "good", "status": "live", "ready": True,
        }

    def _tile_patients(self, scope):
        Move = self.env["account.move"]
        if "is_patient" not in Move._fields:
            return self._needs("patients", "Patients seen", "users",
                               "Patient flag (is_patient) not found on invoices.")
        today = fields.Date.context_today(self)

        def day_stats(d):
            dom = [
                ("move_type", "=", "out_invoice"), ("state", "=", "posted"),
                ("is_patient", "=", True), ("invoice_date", "=", d),
            ] + self._branch_domain(scope)
            moves = Move.search(dom)
            patients = len(moves.mapped("partner_id"))
            rev = sum(moves.mapped("amount_untaxed"))
            return patients, rev

        pt, rev_t = day_stats(today)
        py, _ = day_stats(today - timedelta(days=1))
        pw, _ = day_stats(today - timedelta(days=7))
        rpv = (rev_t / pt) if pt else 0.0
        # cheap 14-day patient-visit count series
        series = []
        for i in range(13, -1, -1):
            series.append(day_stats(today - timedelta(days=i))[0])
        return {
            "key": "patients", "label": "Patients seen", "icon": "users",
            "value": str(pt), "sub": "visits",
            "note": "%s per visit" % self._money(rpv),
            "series": series,
            "delta_yest": self._delta(pt, py), "delta_week": self._delta(pt, pw),
            "tone": "good", "status": "live", "ready": True,
        }

    def _tile_utilization(self, scope):
        if "hms.appointment" not in self.env:
            return self._needs("util", "Chair utilization", "clock",
                               "Appointment model (hms.appointment) not installed.")
        Appt = self.env["hms.appointment"]
        if not {"date", "date_stop", "physician_id"} <= set(Appt._fields):
            return self._needs("util", "Chair utilization", "clock",
                               "Appointment date/physician fields not found.")
        today = fields.Date.context_today(self)
        start, end = self._day_bounds(today)
        dom = [
            ("date", ">=", fields.Datetime.to_string(start)),
            ("date", "<=", fields.Datetime.to_string(end)),
            ("physician_id", "!=", False),
        ] + self._branch_domain(scope, "hms.appointment")
        appts = Appt.search(dom)
        booked = 0.0
        for a in appts:
            if a.date and a.date_stop and a.date_stop > a.date:
                booked += (a.date_stop - a.date).total_seconds() / 3600.0
        hours = float(self.env["ir.config_parameter"].sudo().get_param(
            "shafic_pulse.hours_per_physician", default="8") or 8)
        working = len(appts.mapped("physician_id"))
        target = float(self.env["ir.config_parameter"].sudo().get_param(
            "shafic_pulse.target_util", default="75") or 75)
        avail = working * hours
        util = (booked / avail * 100.0) if avail else 0.0
        tone = "good" if util >= target else ("warn" if util >= target - 10 else "crit")
        return {
            "key": "util", "label": "Chair utilization", "icon": "clock",
            "value": self._pct(util), "sub": "/ %s%%" % int(target),
            "note": "%.0fh booked / %.0fh open" % (booked, avail),
            "series": [], "delta_yest": False, "delta_week": False,
            "tone": tone, "status": "partial", "ready": False,
            "hint": "Open hours assume %s h/physician/day (configurable)." % int(hours),
        }

    def _tile_cash(self, scope):
        if "pos.session" not in self.env:
            return self._needs("cash", "Cash variance", "wallet",
                               "POS not installed — no cash sessions to read.")
        Sess = self.env["pos.session"]
        diff_field = next((f for f in ("cash_register_difference",
                                       "cash_real_difference") if f in Sess._fields), None)
        if not diff_field:
            return self._needs("cash", "Cash variance", "wallet",
                               "No cash-difference field on POS sessions. Wire the "
                               "POS cashier-bonus module for per-cashier variance.")
        today = fields.Date.context_today(self)
        start, end = self._day_bounds(today)
        dom = [
            ("state", "=", "closed"),
            ("stop_at", ">=", fields.Datetime.to_string(start)),
            ("stop_at", "<=", fields.Datetime.to_string(end)),
        ]
        sessions = Sess.search(dom)
        tol = float(self.env["ir.config_parameter"].sudo().get_param(
            "shafic_pulse.cash_tolerance", default="10") or 10)
        rows, net, flagged = [], 0.0, 0
        for s in sessions:
            diff = getattr(s, diff_field, 0.0) or 0.0
            net += diff
            over = abs(diff) >= tol
            flagged += 1 if over else 0
            rows.append({
                "left": "%s · %s" % (s.config_id.display_name or "POS",
                                     s.user_id.name or "—"),
                "right": "—" if abs(diff) < 1e-9 else self._money(diff),
                "tone": "crit" if over else ("warn" if diff < 0 else "mute"),
            })
        tone = "crit" if flagged else ("warn" if abs(net) > 5 else "good")
        return {
            "key": "cash", "label": "Cash variance", "icon": "wallet",
            "value": self._money(net), "sub": "net today",
            "note": ("%d over ±%s" % (flagged, self._money(tol))) if flagged
                    else "within tolerance",
            "series": [], "delta_yest": False, "delta_week": False,
            "details": rows, "details_label": "%d sessions" % len(sessions),
            "tone": tone, "status": "live", "ready": True,
        }

    def _tile_capture(self, scope):
        if "shafic.script.capture" not in self.env:
            return self._needs("capture", "Script capture", "pill",
                               "Install / upgrade Shafic Clinic Performance to "
                               "compute script capture.")
        today = fields.Date.context_today(self)
        first = today.replace(day=1)
        rows = self.env["shafic.script.capture"].sudo().read_group(
            [("date", ">=", fields.Date.to_string(first)),
             ("date", "<=", fields.Date.to_string(today))],
            ["captured_value:sum", "prescribed_value:sum",
             "captured_count:sum", "line_count:sum"], [])
        r = rows[0] if rows else {}
        presc = r.get("prescribed_value") or 0.0
        capv = r.get("captured_value") or 0.0
        lines = int(r.get("line_count") or 0)
        capc = int(r.get("captured_count") or 0)
        if lines == 0:
            t = self._needs("capture", "Script capture", "pill",
                            "No prescriptions this month yet.")
            t.update({"value": "\u2014", "ready": True, "status": "live", "tone": "good"})
            return t
        rate = (capv / presc * 100.0) if presc else 0.0
        target = float(self._param("capture_target", "75") or 75)
        tone = "good" if rate >= target else ("warn" if rate >= target - 15 else "crit")
        return {"key": "capture", "label": "Script capture \u00b7 MTD", "icon": "pill",
                "value": self._pct(rate), "sub": "by value",
                "note": "%d of %d lines filled with us \u00b7 %s of %s" % (
                    capc, lines, self._money(capv), self._money(presc)),
                "series": [], "delta_yest": False, "delta_week": False,
                "tone": tone, "status": "live", "ready": True,
                "hint": "Captured = prescribed product sold to the patient within "
                        "the capture window (POS or patient invoice)."}

    def _tile_insurance(self, scope):
        model = next((m for m in ("pharmacy.insurance.claim", "hms.insurance.claim")
                      if m in self.env), None)
        if not model:
            return self._needs("insurance", "Insurance stuck", "shield",
                               "Insurance claim model not found. Wire the unified "
                               "pharmacy.insurance.claim to age stuck claims.")
        return self._needs("insurance", "Insurance stuck", "shield",
                           "Claim model present; aging logic pending model "
                           "unification (submitted & unpaid > threshold days).")

    def _tile_stockouts(self, scope):
        if "stock.quant" not in self.env:
            return self._needs("stock", "A-class stockouts", "package",
                               "Inventory (stock) not installed.")
        if "pos.order.line" not in self.env:
            return self._needs("stock", "A-class stockouts", "package",
                               "No POS sales history to rank top sellers.")
        today = fields.Date.context_today(self)
        since, _ = self._day_bounds(today - timedelta(days=PERIOD_DAYS))
        n = int(self.env["ir.config_parameter"].sudo().get_param(
            "shafic_pulse.aclass_count", default="40") or 40)
        # only inventory-tracked products can be "out of stock"
        PP = self.env["product.product"]
        if "is_storable" in PP._fields:          # Odoo 18
            storable_dom = [("product_id.is_storable", "=", True)]
        else:                                     # older fallback
            storable_dom = [("product_id.type", "=", "product")]
        # rank top sellers by quantity over the window
        grp = self.env["pos.order.line"].read_group(
            [("order_id.date_order", ">=", fields.Datetime.to_string(since)),
             ("order_id.state", "in", ["paid", "done", "invoiced"]),
             ("product_id", "!=", False)] + storable_dom,
            ["qty:sum"], ["product_id"], orderby="qty desc", limit=n)
        prod_ids = [g["product_id"][0] for g in grp if g.get("product_id")]
        qty_map = {g["product_id"][0]: g["qty"] for g in grp if g.get("product_id")}
        if not prod_ids:
            t = self._needs("stock", "A-class stockouts", "package",
                            "No sales in the last %d days to rank." % PERIOD_DAYS)
            t["value"] = "0"
            t["sub"] = "SKUs out"
            return t
        # on-hand for those products in internal locations
        onhand = self.env["stock.quant"].read_group(
            [("product_id", "in", prod_ids), ("location_id.usage", "=", "internal")],
            ["quantity:sum"], ["product_id"])
        oh_map = {g["product_id"][0]: g["quantity"] for g in onhand if g.get("product_id")}
        products = self.env["product.product"].browse(prod_ids)
        out, walked, rows = 0, 0.0, []
        for p in products:
            if (oh_map.get(p.id, 0.0) or 0.0) <= 0.0:
                out += 1
                q90 = qty_map.get(p.id, 0.0)
                daily = q90 / PERIOD_DAYS
                walked += daily * (p.lst_price or p.list_price or 0.0)
                rows.append({
                    "left": p.display_name,
                    "right": "%.0f/wk" % (q90 / (PERIOD_DAYS / 7.0)),
                    "tone": "warn",
                })
        rows.sort(key=lambda r: float(r["right"].split("/")[0]), reverse=True)
        return {
            "key": "stock", "label": "A-class stockouts", "icon": "package",
            "value": str(out), "sub": "SKUs out",
            "note": "top sellers with zero on-hand",
            "extra": "~%s/day" % self._money(walked),
            "series": [], "delta_yest": False, "delta_week": False,
            "details": rows[:8], "details_label": "view items",
            "tone": "warn" if out else "good", "status": "live", "ready": True,
        }

    # ------------------------------------------------------------------ #
    # helpers for graceful degradation
    # ------------------------------------------------------------------ #
    def _needs(self, key, label, icon, reason):
        return {
            "key": key, "label": label, "icon": icon,
            "value": "—", "sub": "", "note": reason,
            "series": [], "delta_yest": False, "delta_week": False,
            "tone": "warn", "status": "needs_source", "ready": False,
        }

    def _safe(self, fn, key, label, icon):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            _logger.exception("pulse tile %s failed", key)
            t = self._needs(key, label, icon, "Could not compute: %s" % e)
            t["status"] = "error"
            return t

    # ------------------------------------------------------------------ #
    # public endpoint
    # ------------------------------------------------------------------ #
    @api.model
    def get_pulse(self, scope="all"):
        tiles = [
            self._safe(lambda: self._tile_margin(scope), "margin", "Gross margin", "activity"),
            self._safe(lambda: self._tile_patients(scope), "patients", "Patients seen", "users"),
            self._safe(lambda: self._tile_utilization(scope), "util", "Chair utilization", "clock"),
            self._safe(lambda: self._tile_cash(scope), "cash", "Cash variance", "wallet"),
            self._safe(lambda: self._tile_capture(scope), "capture", "Script capture", "pill"),
            self._safe(lambda: self._tile_insurance(scope), "insurance", "Insurance stuck", "shield"),
            self._safe(lambda: self._tile_stockouts(scope), "stock", "A-class stockouts", "package"),
        ]

        # triage: worst-first, built from whatever computed
        triage = []
        by_key = {t["key"]: t for t in tiles}
        cash = by_key.get("cash", {})
        for r in cash.get("details", []) or []:
            if r.get("tone") == "crit":
                triage.append({"tone": "crit", "label": "Cash short: %s" % r["left"]})
        stock = by_key.get("stock", {})
        if stock.get("status") == "live" and stock.get("value", "0") not in ("0", "—"):
            triage.append({"tone": "urgent", "label": "%s A-class SKUs out · %s" % (
                stock.get("value"), stock.get("extra", ""))})
        util = by_key.get("util", {})
        if util.get("status") in ("live", "partial") and util.get("tone") in ("warn", "crit"):
            triage.append({"tone": "watch", "label": "Chair use %s" % util.get("value")})
        order = {"crit": 0, "urgent": 1, "watch": 2}
        triage.sort(key=lambda x: order.get(x["tone"], 9))

        tz = self._tz()
        as_of = datetime.now(tz).strftime("%A, %d %B %Y · %H:%M")

        branches = [{"key": "all", "name": "All branches"}] + self._branches()

        sources = [
            {"name": t["label"], "status": t["status"], "detail": t.get("note", "")}
            for t in tiles
        ]

        return self._envelope(scope, tiles, triage)

    # ------------------------------------------------------------------ #
    # shared response envelope
    # ------------------------------------------------------------------ #
    def _envelope(self, scope, tiles, triage):
        order = {"crit": 0, "urgent": 1, "watch": 2}
        triage = sorted(triage, key=lambda x: order.get(x["tone"], 9))
        as_of = datetime.now(self._tz()).strftime("%A, %d %B %Y · %H:%M")
        branches = [{"key": "all", "name": "All branches"}] + self._branches()
        sources = [{"name": t["label"], "status": t["status"],
                    "detail": t.get("note", "")} for t in tiles]
        return {
            "as_of": as_of, "scope": scope, "branches": branches,
            "triage": triage, "tiles": tiles, "sources": sources,
        }

    # ------------------------------------------------------------------ #
    # Tier-2 : Operations
    # ------------------------------------------------------------------ #
    def _param(self, key, default):
        return self.env["ir.config_parameter"].sudo().get_param(
            "shafic_pulse." + key, default=default)

    def _internal_qty_by_product(self):
        rows = self.env["stock.quant"].read_group(
            [("location_id.usage", "=", "internal"), ("quantity", ">", 0)],
            ["quantity:sum"], ["product_id"])
        return {r["product_id"][0]: r["quantity"] for r in rows if r.get("product_id")}

    def _booked_hours_today(self, scope):
        if "hms.appointment" not in self.env:
            return 0.0
        Appt = self.env["hms.appointment"]
        if not {"date", "date_stop"} <= set(Appt._fields):
            return 0.0
        today = fields.Date.context_today(self)
        start, end = self._day_bounds(today)
        appts = Appt.search(
            [("date", ">=", fields.Datetime.to_string(start)),
             ("date", "<=", fields.Datetime.to_string(end))]
            + self._branch_domain(scope, "hms.appointment"))
        h = 0.0
        for a in appts:
            if a.date and a.date_stop and a.date_stop > a.date:
                h += (a.date_stop - a.date).total_seconds() / 3600.0
        return h

    def _op_expiry(self, scope):
        if "stock.lot" not in self.env or "stock.quant" not in self.env:
            return self._needs("expiry", "Near-expiry exposure", "clock",
                               "Inventory / lot tracking not available.")
        Lot = self.env["stock.lot"]
        if "expiration_date" not in Lot._fields:
            return self._needs("expiry", "Near-expiry exposure", "clock",
                               "Expiry tracking (product_expiry) not installed.")
        today = fields.Date.context_today(self)
        near = int(self._param("expiry_days_near", "30") or 30)
        window = int(self._param("expiry_days_window", "90") or 90)
        qrows = self.env["stock.quant"].read_group(
            [("location_id.usage", "=", "internal"), ("quantity", ">", 0),
             ("lot_id", "!=", False)], ["quantity:sum"], ["lot_id"])
        lot_qty = {r["lot_id"][0]: r["quantity"] for r in qrows if r.get("lot_id")}
        if not lot_qty:
            t = self._needs("expiry", "Near-expiry exposure", "clock", "No on-hand lots.")
            t.update({"value": "$0", "sub": "\u2264%dd" % near, "ready": True,
                      "status": "live", "tone": "good"})
            return t
        near_dt, win_dt = today + timedelta(days=near), today + timedelta(days=window)
        val_near = val_win = 0.0
        rows = []
        for lot in Lot.browse(list(lot_qty)):
            exp = lot.expiration_date
            if not exp:
                continue
            exp = exp.date() if hasattr(exp, "date") else exp
            if exp <= win_dt:
                v = lot_qty.get(lot.id, 0.0) * (lot.product_id.standard_price or 0.0)
                val_win += v
                if exp <= near_dt:
                    val_near += v
                rows.append({"left": "%s \u00b7 %s" % (lot.product_id.display_name, exp),
                             "right": self._money(v),
                             "tone": "crit" if exp <= near_dt else "warn", "_v": v})
        rows.sort(key=lambda r: r["_v"], reverse=True)
        for r in rows:
            r.pop("_v", None)
        tone = "crit" if val_near > 0 else ("warn" if val_win > 0 else "good")
        return {"key": "expiry", "label": "Near-expiry exposure", "icon": "clock",
                "value": self._money(val_near), "sub": "\u2264%dd" % near,
                "note": "%s within %dd" % (self._money(val_win), window),
                "series": [], "delta_yest": False, "delta_week": False,
                "details": rows[:8], "details_label": "view lots",
                "tone": tone, "status": "live", "ready": True}

    def _op_stock_value(self, scope):
        if "stock.quant" not in self.env:
            return self._needs("stockval", "Stock value on hand", "package",
                               "Inventory not installed.")
        Q = self.env["stock.quant"]
        if "value" in Q._fields:
            rows = Q.read_group([("location_id.usage", "=", "internal")], ["value:sum"], [])
            val = (rows[0]["value"] if rows and rows[0].get("value") else 0.0)
        else:
            m = self._internal_qty_by_product()
            val = sum(m.get(p.id, 0.0) * (p.standard_price or 0.0)
                      for p in self.env["product.product"].browse(list(m)))
        return {"key": "stockval", "label": "Stock value on hand", "icon": "package",
                "value": self._money(val), "sub": "at cost", "note": "cash tied up in inventory",
                "series": [], "delta_yest": False, "delta_week": False,
                "tone": "good", "status": "live", "ready": True}

    def _op_dead_stock(self, scope):
        if "stock.quant" not in self.env or "pos.order.line" not in self.env:
            return self._needs("dead", "Dead stock", "package",
                               "Needs inventory and POS sales history.")
        days = int(self._param("deadstock_days", "90") or 90)
        today = fields.Date.context_today(self)
        since, _ = self._day_bounds(today - timedelta(days=days))
        sold = set()
        for r in self.env["pos.order.line"].read_group(
                [("order_id.date_order", ">=", fields.Datetime.to_string(since)),
                 ("product_id", "!=", False)], ["qty:sum"], ["product_id"]):
            if r.get("product_id"):
                sold.add(r["product_id"][0])
        onhand = self._internal_qty_by_product()
        val, cnt, rows = 0.0, 0, []
        for p in self.env["product.product"].browse(list(onhand)):
            if p.id not in sold:
                v = onhand.get(p.id, 0.0) * (p.standard_price or 0.0)
                if v > 0:
                    val += v
                    cnt += 1
                    rows.append({"left": p.display_name, "right": self._money(v),
                                 "tone": "warn", "_v": v})
        rows.sort(key=lambda r: r["_v"], reverse=True)
        for r in rows:
            r.pop("_v", None)
        return {"key": "dead", "label": "Dead stock", "icon": "package",
                "value": self._money(val), "sub": "%d items" % cnt,
                "note": "no sale in %d days" % days,
                "series": [], "delta_yest": False, "delta_week": False,
                "details": rows[:8], "details_label": "view items",
                "tone": "warn" if val > 0 else "good", "status": "live", "ready": True}

    def _op_receivables(self, scope):
        Move = self.env["account.move"]
        today = fields.Date.context_today(self)
        moves = Move.search(
            [("move_type", "=", "out_invoice"), ("state", "=", "posted"),
             ("payment_state", "in", ("not_paid", "partial")),
             ("amount_residual", ">", 0)] + self._branch_domain(scope))
        buckets = {"Current": 0.0, "1-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
        for m in moves:
            due = m.invoice_date_due or m.invoice_date or today
            d = (today - due).days
            amt = m.amount_residual
            key = ("Current" if d <= 0 else "1-30" if d <= 30 else "31-60"
                   if d <= 60 else "61-90" if d <= 90 else "90+")
            buckets[key] += amt
        total = sum(buckets.values())
        overdue = total - buckets["Current"]
        rows = [{"left": k, "right": self._money(v),
                 "tone": "crit" if k == "90+" else "warn" if k in ("31-60", "61-90")
                 else "mute"} for k, v in buckets.items() if v]
        tone = "crit" if buckets["90+"] > 0 else ("warn" if overdue > 0 else "good")
        return {"key": "ar", "label": "Receivables (overdue)", "icon": "wallet",
                "value": self._money(overdue), "sub": "overdue",
                "note": "%s total open AR" % self._money(total),
                "series": [], "delta_yest": False, "delta_week": False,
                "details": rows, "details_label": "by age",
                "tone": tone, "status": "live", "ready": True}

    def _op_payment_mix(self, scope):
        today = fields.Date.context_today(self)
        start, end = self._day_bounds(today)
        mix = {}
        if "pos.payment" in self.env:
            for r in self.env["pos.payment"].read_group(
                    [("payment_date", ">=", fields.Datetime.to_string(start)),
                     ("payment_date", "<=", fields.Datetime.to_string(end))],
                    ["amount:sum"], ["payment_method_id"]):
                if r.get("payment_method_id"):
                    mix[r["payment_method_id"][1]] = mix.get(
                        r["payment_method_id"][1], 0.0) + (r["amount"] or 0.0)
        if "account.payment" in self.env:
            Pay = self.env["account.payment"]
            dom = [("date", "=", today), ("payment_type", "=", "inbound")]
            if "state" in Pay._fields:
                dom += [("state", "not in", ("draft", "cancel", "canceled"))]
            for r in Pay.read_group(dom, ["amount:sum"], ["journal_id"]):
                if r.get("journal_id"):
                    mix[r["journal_id"][1]] = mix.get(
                        r["journal_id"][1], 0.0) + (r["amount"] or 0.0)
        total = sum(mix.values())
        if not mix:
            t = self._needs("paymix", "Payment mix", "wallet", "No collections recorded today yet.")
            t.update({"value": "$0", "ready": True, "status": "live", "tone": "good"})
            return t
        ordered = sorted(mix.items(), key=lambda kv: kv[1], reverse=True)
        rows = [{"left": k, "right": "%s (%s)" % (self._money(v),
                 self._pct(v / total * 100.0 if total else 0)), "tone": "mute"}
                for k, v in ordered]
        top = ordered[0]
        return {"key": "paymix", "label": "Payment mix · today", "icon": "wallet",
                "value": self._money(total), "sub": "collected",
                "note": "top: %s %s" % (top[0], self._pct(top[1] / total * 100.0 if total else 0)),
                "series": [], "delta_yest": False, "delta_week": False,
                "details": rows[:8], "details_label": "by method",
                "tone": "good", "status": "live", "ready": True}

    def _op_appointments(self, scope):
        if "hms.appointment" not in self.env:
            return self._needs("appt", "Appointment completion", "users",
                               "Appointment model not installed.")
        Appt = self.env["hms.appointment"]
        today = fields.Date.context_today(self)
        start, end = self._day_bounds(today)
        base = [("date", ">=", fields.Datetime.to_string(start)),
                ("date", "<=", fields.Datetime.to_string(end))] \
            + self._branch_domain(scope, "hms.appointment")
        scheduled = Appt.search_count(base + [("state", "!=", "cancel")])
        done = Appt.search_count(base + [("state", "=", "done")])
        active = Appt.search_count(base + [("state", "in",
                                            ("waiting", "in_consultation", "pause"))])
        target = float(self._param("appt_target", "80") or 80)
        comp = (done / scheduled * 100.0) if scheduled else 0.0
        tone = "good" if comp >= target else ("warn" if comp >= target - 15 else "crit")
        return {"key": "appt", "label": "Appointment completion", "icon": "users",
                "value": self._pct(comp), "sub": "/ %d%%" % int(target),
                "note": "%d done, %d in progress of %d" % (done, active, scheduled),
                "series": [], "delta_yest": False, "delta_week": False,
                "tone": tone if scheduled else "good", "status": "live", "ready": True}

    def _op_rev_per_hour(self, scope):
        today = fields.Date.context_today(self)
        rev, _ = self._invoice_rev_cogs(today, scope)
        booked = self._booked_hours_today(scope)
        if booked <= 0:
            return self._needs("revhour", "Revenue / physician-hour", "activity",
                               "No booked physician hours today.")
        rph = rev / booked
        return {"key": "revhour", "label": "Revenue / physician-hour", "icon": "activity",
                "value": self._money(rph), "sub": "per hour",
                "note": "%s over %.0fh booked" % (self._money(rev), booked),
                "series": [], "delta_yest": False, "delta_week": False,
                "tone": "good", "status": "live", "ready": True}

    @api.model
    def get_operations(self, scope="all"):
        tiles = [
            self._safe(lambda: self._op_expiry(scope), "expiry", "Near-expiry exposure", "clock"),
            self._safe(lambda: self._op_receivables(scope), "ar", "Receivables (overdue)", "wallet"),
            self._safe(lambda: self._op_payment_mix(scope), "paymix", "Payment mix", "wallet"),
            self._safe(lambda: self._op_appointments(scope), "appt", "Appointment completion", "users"),
            self._safe(lambda: self._op_rev_per_hour(scope), "revhour", "Revenue / physician-hour", "activity"),
            self._safe(lambda: self._op_dead_stock(scope), "dead", "Dead stock", "package"),
            self._safe(lambda: self._op_stock_value(scope), "stockval", "Stock value on hand", "package"),
        ]
        by = {t["key"]: t for t in tiles}
        triage = []
        exp = by.get("expiry", {})
        if exp.get("status") == "live" and exp.get("value") not in ("$0", "—"):
            triage.append({"tone": "urgent", "label": "Near-expiry %s %s" % (exp.get("value"), exp.get("sub", ""))})
        ar = by.get("ar", {})
        for r in ar.get("details", []) or []:
            if r.get("left") == "90+" and r.get("right") not in ("$0", "—"):
                triage.append({"tone": "urgent", "label": "AR 90+ days: %s" % r["right"]})
        appt = by.get("appt", {})
        if appt.get("status") == "live" and appt.get("tone") in ("warn", "crit"):
            triage.append({"tone": "watch", "label": "Appointment completion %s" % appt.get("value")})
        dead = by.get("dead", {})
        if dead.get("status") == "live" and dead.get("value") not in ("$0", "—"):
            triage.append({"tone": "watch", "label": "Dead stock %s" % dead.get("value")})
        return self._envelope(scope, tiles, triage)

    # ------------------------------------------------------------------ #
    # Physician scorecard (reads the Clinic Performance analysis view)
    # ------------------------------------------------------------------ #
    @api.model
    def get_physicians(self, scope="all"):
        base = {
            "as_of": datetime.now(self._tz()).strftime("%A, %d %B %Y \u00b7 %H:%M"),
            "scope": scope, "view": "physicians", "period": "This month",
            "branches": [{"key": "all", "name": "All branches"}] + self._branches(),
            "physicians": [], "service_order": [], "total_revenue_str": self._money(0),
        }
        if "shafic.physician.performance" not in self.env:
            base["message"] = ("Install / upgrade Shafic Clinic Performance to use "
                               "the physician scorecard.")
            return base
        today = fields.Date.context_today(self)
        first = today.replace(day=1)
        PP = self.env["shafic.physician.performance"].sudo()
        dom = [("invoice_date", ">=", fields.Date.to_string(first)),
               ("invoice_date", "<=", fields.Date.to_string(today))]
        try:
            g1 = PP.read_group(dom, ["revenue:sum", "line_count:sum"],
                               ["physician_id", "service_type"], lazy=False)
            g2 = PP.read_group(dom, ["revenue:sum"],
                               ["physician_id", "payment_state"], lazy=False)
            g3 = PP.read_group(dom, [], ["physician_id", "patient_id"], lazy=False)
        except Exception as e:  # noqa: BLE001
            base["message"] = "Could not read performance data: %s" % e
            return base

        phys, svc_tot = {}, {}

        def ent(pt):
            key = pt[0] if pt else "unassigned"
            if key not in phys:
                phys[key] = {"key": str(key), "name": (pt[1] if pt else "Unassigned"),
                             "unassigned": not bool(pt), "revenue": 0.0, "lines": 0,
                             "mix": {}, "paid": 0.0, "outstanding": 0.0, "patients": 0,
                             "rx_count": 0, "rx_value": 0.0, "cap_value": 0.0, "presc_value": 0.0}
            return phys[key]

        for r in g1:
            e = ent(r.get("physician_id"))
            rev = r.get("revenue") or 0.0
            e["revenue"] += rev
            e["lines"] += int(r.get("line_count") or 0)
            st = r.get("service_type") or "Other"
            e["mix"][st] = e["mix"].get(st, 0.0) + rev
            svc_tot[st] = svc_tot.get(st, 0.0) + rev
        for r in g2:
            e = ent(r.get("physician_id"))
            rev = r.get("revenue") or 0.0
            if r.get("payment_state") == "paid":
                e["paid"] += rev
            else:
                e["outstanding"] += rev
        for r in g3:
            ent(r.get("physician_id"))["patients"] += 1

        # prescriptions written + value (from the prescription analysis view)
        if "shafic.physician.prescription" in self.env:
            try:
                for r in self.env["shafic.physician.prescription"].sudo().read_group(
                        [("date", ">=", fields.Date.to_string(first)),
                         ("date", "<=", fields.Date.to_string(today))],
                        ["prescription_count:sum", "value:sum"],
                        ["physician_id"], lazy=False):
                    e = ent(r.get("physician_id"))
                    e["rx_count"] += int(r.get("prescription_count") or 0)
                    e["rx_value"] += r.get("value") or 0.0
            except Exception:  # noqa: BLE001
                pass

        # script capture (dispensed with us) per physician
        if "shafic.script.capture" in self.env:
            try:
                for r in self.env["shafic.script.capture"].sudo().read_group(
                        [("date", ">=", fields.Date.to_string(first)),
                         ("date", "<=", fields.Date.to_string(today))],
                        ["captured_value:sum", "prescribed_value:sum"],
                        ["physician_id"], lazy=False):
                    e = ent(r.get("physician_id"))
                    e["cap_value"] += r.get("captured_value") or 0.0
                    e["presc_value"] += r.get("prescribed_value") or 0.0
            except Exception:  # noqa: BLE001
                pass

        total = sum(e["revenue"] for e in phys.values()) or 0.0
        total_rx = sum(e["rx_count"] for e in phys.values())
        total_rx_value = sum(e["rx_value"] for e in phys.values())
        total_cap = sum(e["cap_value"] for e in phys.values())
        total_presc = sum(e["presc_value"] for e in phys.values())
        assigned = sorted([e for e in phys.values() if not e["unassigned"]],
                          key=lambda x: x["revenue"], reverse=True)
        unassigned = [e for e in phys.values() if e["unassigned"]]
        out, rank = [], 0
        for e in assigned + unassigned:
            if not e["unassigned"]:
                rank += 1
            ptot = e["revenue"] or 1.0
            mix = sorted(e["mix"].items(), key=lambda kv: kv[1], reverse=True)
            out.append({
                "key": e["key"], "name": e["name"], "unassigned": e["unassigned"],
                "rank": (rank if not e["unassigned"] else 0),
                "revenue_str": self._money(e["revenue"]),
                "share_pct": round(e["revenue"] / total * 100, 1) if total else 0.0,
                "patients": e["patients"], "lines": e["lines"],
                "paid_str": self._money(e["paid"]), "outstanding_str": self._money(e["outstanding"]),
                "rx_count": e["rx_count"], "rx_value_str": self._money(e["rx_value"]),
                "capture_str": (self._pct(e["cap_value"] / e["presc_value"] * 100.0)
                                if e["presc_value"] else "—"),
                "mix": [{"type": k, "revenue_str": self._money(v),
                         "pct": round(v / ptot * 100, 1)} for k, v in mix],
            })
        base["physicians"] = out
        base["service_order"] = [k for k, _ in sorted(
            svc_tot.items(), key=lambda kv: kv[1], reverse=True)]
        base["total_revenue_str"] = self._money(total)
        base["total_rx"] = total_rx
        base["total_rx_value_str"] = self._money(total_rx_value)
        base["total_capture_str"] = (self._pct(total_cap / total_presc * 100.0)
                                     if total_presc else "—")
        return base
