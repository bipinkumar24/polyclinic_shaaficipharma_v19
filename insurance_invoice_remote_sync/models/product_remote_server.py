# -*- coding: utf-8 -*-
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# The ONLY records this module ever touches - confirmed against the live
# source (187/187 posted) via the same domain already used in this codebase's
# own "Insurance Invoice" menu (acs_hms_cashier.action_hms_insurance_invoice).
# Never widen this domain: vendor bills, credit notes, plain customer
# invoices and journal entries must never be pulled in.
INSURANCE_INVOICE_DOMAIN = [("move_type", "=", "out_invoice"), ("patient_invoice_amount", ">", 0)]

HEADER_FIELDS = [
    "id", "name", "ref", "invoice_date", "invoice_date_due", "journal_id", "currency_id",
    "company_id", "branch_id", "partner_id", "patient_id", "invoice_user_id", "team_id",
    "payment_reference", "state", "physician_id", "hospital_invoice_type",
    "patient_invoice_id", "patient_invoice_amount", "commission_type", "commission_created",
    "commission_ids", "invoice_line_ids",
]
LINE_FIELDS = ["product_id", "name", "quantity", "product_uom_id", "price_unit", "discount", "tax_ids"]
COMMISSION_FIELDS = [
    "name", "state", "partner_id", "commission_on", "commission_amount", "payable_amount",
    "payment_status", "date", "target_based_commission",
]


class ProductRemoteServer(models.Model):
    _inherit = "product.remote.server"

    insurance_invoice_count = fields.Integer(
        string="Synced Insurance Invoices", compute="_compute_insurance_invoice_count"
    )
    insurance_invoice_skip_log = fields.Text(
        string="Insurance Invoice Skip Log", readonly=True, copy=False,
        help="Remote id/name/reason for every insurance invoice that was skipped "
             "during the last sync run (never fabricated, always logged).",
    )
    insurance_invoice_validation_report = fields.Text(
        string="Insurance Invoice Validation Report", readonly=True, copy=False,
    )

    def _compute_insurance_invoice_count(self):
        Move = self.env["account.move"].with_context(active_test=False)
        for server in self:
            server.insurance_invoice_count = (
                Move.search_count([("remote_server_id", "=", server.id)]) if server.id else 0
            )

    # ------------------------------------------------------------------
    # Generic name-based resolver for accounting configuration objects
    # (branch, journal, sales team, uom) that already exist locally and
    # are never auto-created by this migration.
    # ------------------------------------------------------------------
    def _resolve_by_name(self, comodel, value, cache):
        if not value:
            return False
        name = value[1] if isinstance(value, (list, tuple)) else value
        key = (comodel, "name-match", name)
        if key in cache:
            return cache[key]
        rec = self.env[comodel].search([("name", "=", name)], limit=1)
        cache[key] = rec.id if rec else False
        return cache[key]

    def _resolve_salesperson(self, value, cache):
        if not value:
            return False
        name = value[1] if isinstance(value, (list, tuple)) else value
        key = ("res.users", "salesperson", name)
        if key in cache:
            return cache[key]
        user = self.env["res.users"].sudo().search([("name", "=", name)], limit=1)
        cache[key] = user.id if user else False
        return cache[key]

    def _resolve_taxes(self, remote_tax_ids, uid, proxy, cache):
        if not remote_tax_ids:
            return []
        result = []
        for rid in remote_tax_ids:
            key = ("account.tax", "remote", rid)
            if key not in cache:
                rows = self._execute(
                    uid, proxy, "account.tax", "read", [[rid]],
                    {"fields": ["name", "amount", "type_tax_use"]},
                )
                local = False
                if rows:
                    tax = self.env["account.tax"].search([
                        ("name", "=", rows[0]["name"]),
                        ("amount", "=", rows[0]["amount"]),
                        ("type_tax_use", "=", rows[0]["type_tax_use"]),
                    ], limit=1)
                    local = tax.id if tax else False
                cache[key] = local
            if cache[key]:
                result.append(cache[key])
        return result

    # ------------------------------------------------------------------
    # Invoice lines
    # ------------------------------------------------------------------
    def _prepare_invoice_line_commands(self, uid, proxy, data, cache):
        remote_line_ids = data.get("invoice_line_ids") or []
        if not remote_line_ids:
            return []
        lines = self._execute(
            uid, proxy, "account.move.line", "read", [remote_line_ids], {"fields": LINE_FIELDS}
        )
        commands = []
        for line in lines:
            vals = {
                "name": line.get("name") or "/",
                "quantity": line.get("quantity") or 1.0,
                "price_unit": line.get("price_unit") or 0.0,
                "discount": line.get("discount") or 0.0,
            }
            # product.product itself has no remote tracking - resolved via the
            # already-synced product.template remote_id chain (same helper
            # hms_remote_sync uses for hms.patient.registration_product_id).
            if line.get("product_id"):
                product_id = self._resolve_registration_product(line["product_id"], cache)
                if product_id:
                    vals["product_id"] = product_id
            if line.get("product_uom_id"):
                uom_id = self._resolve_by_name("uom.uom", line["product_uom_id"], cache)
                if uom_id:
                    vals["product_uom_id"] = uom_id
            # Always set tax_ids explicitly, including empty: leaving the key
            # out entirely (when the source line genuinely has no tax) lets
            # Odoo fall back to the product's own default taxes on create,
            # silently adding a tax the source invoice never had.
            tax_ids = self._resolve_taxes(line.get("tax_ids"), uid, proxy, cache)
            vals["tax_ids"] = [(6, 0, tax_ids)]
            commands.append((0, 0, vals))
        return commands

    # ------------------------------------------------------------------
    # Commission records
    # ------------------------------------------------------------------
    def _sync_commissions_for_invoice(self, uid, proxy, data, move, cache):
        remote_commission_ids = data.get("commission_ids") or []
        if not remote_commission_ids:
            return
        rows = self._execute(
            uid, proxy, "acs.commission", "read", [remote_commission_ids], {"fields": COMMISSION_FIELDS}
        )
        Commission = self.env["acs.commission"].sudo()
        for c in rows:
            partner_id = self._resolve_synced_only("res.partner", c.get("partner_id"), cache)
            if not partner_id:
                _logger.warning(
                    "Insurance invoice sync: commission %s (remote id %s) - "
                    "'Commission For' partner not synced locally, skipped.",
                    c.get("name"), c.get("id"),
                )
                continue
            vals = {
                "partner_id": partner_id,
                "invoice_id": move.id,
                "state": c.get("state") or "draft",
                "commission_on": c.get("commission_on") or 0.0,
                "commission_amount": c.get("commission_amount") or 0.0,
                "payable_amount": c.get("payable_amount") or 0.0,
                "payment_status": c.get("payment_status") or "not_inv",
                "date": c.get("date"),
                "target_based_commission": bool(c.get("target_based_commission")),
                "remote_server_id": self.id,
                "remote_id": c["id"],
            }
            if c.get("name"):
                vals["name"] = c["name"]
            existing_c = Commission.with_context(active_test=False).search(
                [("remote_server_id", "=", self.id), ("remote_id", "=", c["id"])], limit=1
            )
            if existing_c:
                existing_c.write(vals)
            else:
                Commission.create(vals)

    # ------------------------------------------------------------------
    # One invoice
    # ------------------------------------------------------------------
    def _sync_one_insurance_invoice(self, uid, proxy, data, cache):
        Move = self.env["account.move"].sudo().with_context(active_test=False)
        existing = Move.search(
            [("remote_server_id", "=", self.id), ("remote_id", "=", data["id"])], limit=1
        )

        if existing:
            # Never rewrite an already-migrated (posted) invoice's header/lines
            # - only keep its commission records in sync, which are separate
            # documents and safe to update.
            self._sync_commissions_for_invoice(uid, proxy, data, existing, cache)
            return "updated"

        partner_id = self._resolve_synced_only("res.partner", data.get("partner_id"), cache)
        if not partner_id:
            raise UserError(
                _("Invoice '%(name)s' (remote id %(rid)s): customer partner not synced "
                  "locally - skipped.") % {"name": data.get("name"), "rid": data.get("id")}
            )
        journal_id = self._resolve_by_name("account.journal", data.get("journal_id"), cache)
        if not journal_id:
            raise UserError(
                _("Invoice '%(name)s' (remote id %(rid)s): journal not found locally - skipped.")
                % {"name": data.get("name"), "rid": data.get("id")}
            )
        branch_id = self._resolve_by_name("res.branch", data.get("branch_id"), cache)
        if data.get("branch_id") and not branch_id:
            raise UserError(
                _("Invoice '%(name)s' (remote id %(rid)s): branch not found locally - skipped.")
                % {"name": data.get("name"), "rid": data.get("id")}
            )

        patient_id = self._resolve_synced_only("hms.patient", data.get("patient_id"), cache)
        physician_id = self._resolve_synced_only("hms.physician", data.get("physician_id"), cache)
        team_id = self._resolve_by_name("crm.team", data.get("team_id"), cache)
        salesperson_id = self._resolve_salesperson(data.get("invoice_user_id"), cache)

        line_commands = self._prepare_invoice_line_commands(uid, proxy, data, cache)

        vals = {
            "move_type": "out_invoice",
            "name": data.get("name"),  # exact historic number - skips sequence assignment
            "ref": data.get("ref"),
            "invoice_date": data.get("invoice_date"),
            "invoice_date_due": data.get("invoice_date_due"),
            "journal_id": journal_id,
            "company_id": (self.company_id or self.env.company).id,
            "partner_id": partner_id,
            "invoice_line_ids": line_commands,
            "remote_server_id": self.id,
            "remote_id": data["id"],
        }
        if branch_id:
            vals["branch_id"] = branch_id
        if patient_id:
            vals["patient_id"] = patient_id
        if physician_id:
            vals["physician_id"] = physician_id
        if team_id:
            vals["team_id"] = team_id
        if salesperson_id:
            vals["invoice_user_id"] = salesperson_id
        if data.get("payment_reference"):
            vals["payment_reference"] = data["payment_reference"]
        if data.get("hospital_invoice_type"):
            vals["hospital_invoice_type"] = data["hospital_invoice_type"]
        if data.get("commission_type"):
            vals["commission_type"] = data["commission_type"]
        vals["commission_created"] = bool(data.get("commission_created"))

        move = Move.create(vals)
        # Confirmed on the source: patient_invoice_id is self-referencing on
        # every one of these 187 records.
        move.patient_invoice_id = move.id
        move.action_post()

        self._sync_commissions_for_invoice(uid, proxy, data, move, cache)
        return "created"

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------
    def _sync_insurance_invoices(self, limit=None):
        self.ensure_one()
        self.env.cr.commit()
        uid, proxy = self._get_connection()
        cache = {}
        created = updated = failed = 0
        skipped = []
        offset = 0
        batch_size = self.batch_size or 100
        while True:
            page_size = batch_size
            if limit:
                remaining = limit - (created + updated + failed)
                if remaining <= 0:
                    break
                page_size = min(batch_size, remaining)
            self.env.cr.commit()
            rows = self._execute(
                uid, proxy, "account.move", "search_read", [INSURANCE_INVOICE_DOMAIN],
                {"fields": HEADER_FIELDS, "order": "id", "limit": page_size, "offset": offset},
            )
            if not rows:
                break
            for data in rows:
                try:
                    with self.env.cr.savepoint():
                        result = self._sync_one_insurance_invoice(uid, proxy, data, cache)
                        if result == "created":
                            created += 1
                        else:
                            updated += 1
                except Exception as exc:
                    failed += 1
                    skipped.append(f"remote id {data.get('id')} ({data.get('name')}): {exc}")
                    _logger.warning(
                        "Insurance invoice sync: failed for remote id %s (%s): %s",
                        data.get("id"), data.get("name"), exc,
                    )
            offset += len(rows)
            self.env.cr.commit()
            _logger.info(
                "Insurance invoice sync from %s: batch committed at offset %s "
                "(created=%s updated=%s failed=%s)",
                self.name, offset, created, updated, failed,
            )
            if len(rows) < batch_size:
                break
        self.insurance_invoice_skip_log = "\n".join(skipped) if skipped else False
        self.last_sync = fields.Datetime.now()
        return {"created": created, "updated": updated, "failed": failed}

    def action_sync_insurance_invoices(self):
        totals = {"created": 0, "updated": 0, "failed": 0}
        for server in self:
            res = server._sync_insurance_invoices()
            for key in totals:
                totals[key] += res[key]
        message = _(
            "Insurance Invoices — Created: %(created)s | Updated: %(updated)s | Failed: %(failed)s"
        ) % totals
        return self._notify(
            _("Insurance invoice sync finished"), message, "warning" if totals["failed"] else "success"
        )

    def action_sync_insurance_invoice_test_batch(self):
        self.ensure_one()
        res = self._sync_insurance_invoices(limit=self.test_limit or 5)
        message = _(
            "Insurance Invoices (test batch) — Created: %(created)s | Updated: %(updated)s | "
            "Failed: %(failed)s"
        ) % res
        return self._notify(
            _("Insurance invoice test batch finished"), message, "warning" if res["failed"] else "success"
        )

    def action_view_insurance_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Synced Insurance Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("remote_server_id", "=", self.id)],
            "context": {"create": False},
        }

    # ------------------------------------------------------------------
    # Validation report - full dataset, not sampled
    # ------------------------------------------------------------------
    def action_validate_insurance_invoices(self):
        self.ensure_one()
        uid, proxy = self._get_connection()
        remote_rows = self._execute(
            uid, proxy, "account.move", "search_read", [INSURANCE_INVOICE_DOMAIN],
            {"fields": HEADER_FIELDS, "order": "id"},
        )
        Move = self.env["account.move"].sudo().with_context(active_test=False)
        local_by_remote_id = {
            m.remote_id: m for m in Move.search([("remote_server_id", "=", self.id)])
        }

        lines = [
            "Insurance Invoice Validation Report",
            "Server: %s" % self.name,
            "Remote total (domain-matched): %s" % len(remote_rows),
            "Local synced total: %s" % len(local_by_remote_id),
            "",
        ]
        mismatches = 0
        missing = 0
        for r in remote_rows:
            local = local_by_remote_id.get(r["id"])
            if not local:
                missing += 1
                lines.append("MISSING LOCALLY: remote id %s (%s)" % (r["id"], r.get("name")))
                continue
            issues = []
            if local.name != r.get("name"):
                issues.append("name: remote=%r local=%r" % (r.get("name"), local.name))
            if local.ref != (r.get("ref") or False):
                issues.append("ref: remote=%r local=%r" % (r.get("ref"), local.ref))
            # patient_invoice_id is self-referencing on these records, so on the
            # source patient_invoice_amount == the invoice's own amount_total.
            if round(local.amount_total, 2) != round(r.get("patient_invoice_amount") or 0.0, 2):
                issues.append(
                    "amount_total: remote=%r local=%r"
                    % (r.get("patient_invoice_amount"), local.amount_total)
                )
            remote_line_count = len(r.get("invoice_line_ids") or [])
            local_line_count = len(local.invoice_line_ids)
            if remote_line_count != local_line_count:
                issues.append(
                    "line count: remote=%s local=%s" % (remote_line_count, local_line_count)
                )
            remote_commission_count = len(r.get("commission_ids") or [])
            local_commission_count = len(local.commission_ids)
            if remote_commission_count != local_commission_count:
                issues.append(
                    "commission count: remote=%s local=%s"
                    % (remote_commission_count, local_commission_count)
                )
            if bool(local.hospital_invoice_type) != bool(r.get("hospital_invoice_type")) or (
                r.get("hospital_invoice_type") and local.hospital_invoice_type != r["hospital_invoice_type"]
            ):
                issues.append(
                    "hospital_invoice_type: remote=%r local=%r"
                    % (r.get("hospital_invoice_type"), local.hospital_invoice_type)
                )
            if local.state != "posted":
                issues.append("state: expected posted, got %r" % local.state)
            if issues:
                mismatches += 1
                lines.append("MISMATCH remote id %s (%s): %s" % (r["id"], r.get("name"), "; ".join(issues)))

        lines.append("")
        lines.append("Summary: %s missing, %s mismatched, %s clean (of %s)" % (
            missing, mismatches, len(remote_rows) - missing - mismatches, len(remote_rows)
        ))
        report_text = "\n".join(lines)
        self.insurance_invoice_validation_report = report_text
        return self._notify(
            _("Insurance invoice validation finished"),
            _("%(missing)s missing, %(mismatches)s mismatched out of %(total)s - see the "
              "Validation Report field for full detail.")
            % {"missing": missing, "mismatches": mismatches, "total": len(remote_rows)},
            "warning" if (missing or mismatches) else "success",
        )
