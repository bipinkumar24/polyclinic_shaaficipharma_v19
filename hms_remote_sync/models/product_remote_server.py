# -*- coding: utf-8 -*-
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.addons.product_remote_sync.models.product_remote_server import (
    EXTRA_READ_FIELDS as _BASE_EXTRA_READ_FIELDS,
)

_logger = logging.getLogger(__name__)

# _sync_model() (inherited unmodified from product_remote_sync) reads its
# EXTRA_READ_FIELDS module-level constant directly by name, with no per-model
# override hook. The fields excluded from our field plan above (partner_id,
# insurance_company_id, nationality_id, registration_product_id) still need to
# be *read* from the remote so our manual resolvers in _prepare_vals() have
# raw values to work with - so we add them to that same dict object.
#
# CAUTION (root cause of a prior data-corruption bug): hms.patient/hms.physician
# _inherits res.partner/res.users, and in this Odoo version EVERY _inherits-
# delegated field (name, code, birthday, phone, address, ...) is a store=False
# related field. The generic plan builder only handles stored fields, so it
# silently drops all of them from the sync plan - INCLUDING `name`. But the
# base _prepare_vals() has an unconditional fallback:
#   if "name" in Model._fields and not vals.get("name"): vals["name"] = "Unnamed"
# Since `name` is dropped from the plan, that fallback fires on every hms.patient/
# hms.physician create() call, injecting vals["name"] = "Unnamed" - and because
# partner_id/user_id is given explicitly, Odoo's multi-level _inherits create()
# WRITES that "Unnamed" straight through to the (already correctly-named,
# already-synced) target partner, overwriting real data. `code` has the same
# store=False problem without a dangerous fallback (it's just silently omitted),
# so it also needs restoring explicitly. _prepare_vals() below handles `name`
# for both models explicitly (never letting the base fallback fire) and reads
# `code`/`partner_id` back in for hms.patient's own preservation/resolution.
for _field in (
    "partner_id",
    "insurance_company_id",
    "nationality_id",
    "registration_product_id",
    "code",
    "name",
):
    if _field not in _BASE_EXTRA_READ_FIELDS.setdefault("hms.patient", []):
        _BASE_EXTRA_READ_FIELDS["hms.patient"].append(_field)

for _field in ("partner_id", "name"):
    if _field not in _BASE_EXTRA_READ_FIELDS.setdefault("hms.physician", []):
        _BASE_EXTRA_READ_FIELDS["hms.physician"].append(_field)

# Fields excluded from the generic per-model field plan for HMS models: either
# they need stricter/manual resolution (never falling back to a name match
# that could mis-link two different people/companies sharing a name), or they
# are explicitly deferred out of this migration's master-data scope.
HMS_PLAN_EXCLUDED_FIELDS = {
    "hms.patient": {
        "partner_id",  # resolved manually: remote_id-only match, row skipped if unresolved
        "user_id",  # portal-user link, not master data
        "insurance_company_id",  # resolved manually: remote_id-only match, optional
        "nationality_id",  # resolved manually via res.country.code (translation-proof)
        "registration_product_id",  # resolved manually via the product.template remote_id chain
        # Deferred master-data follow-ups (see migration plan) - not synced in v1:
        "corpo_company_id",
        "ref_doctor_ids",
        "acs_tag_ids",
        "document_type_id",
        "acs_religion_id",
        "ethnic_group_id",
    },
    "hms.physician": {
        "user_id",
        "login",
        "password",  # handled manually: unique login, forced Portal-only access
    },
}

# Simple name-keyed lookup tables physicians depend on (UNIQUE(name), no
# remote_id tracking of their own) - synced create-if-missing before physicians.
HMS_LOOKUP_MODELS = ("physician.specialty", "physician.degree")


class ProductRemoteServer(models.Model):
    _inherit = "product.remote.server"

    hms_patient_count = fields.Integer(
        string="Synced Patients", compute="_compute_hms_sync_counts"
    )
    hms_physician_count = fields.Integer(
        string="Synced Physicians", compute="_compute_hms_sync_counts"
    )
    hms_department_count = fields.Integer(
        string="Synced Departments", compute="_compute_hms_sync_counts"
    )

    def _compute_hms_sync_counts(self):
        Patient = self.env["hms.patient"].with_context(active_test=False)
        Physician = self.env["hms.physician"].with_context(active_test=False)
        Department = self.env["hr.department"].with_context(active_test=False)
        for server in self:
            domain = [("remote_server_id", "=", server.id)] if server.id else None
            server.hms_patient_count = Patient.search_count(domain) if domain else 0
            server.hms_physician_count = Physician.search_count(domain) if domain else 0
            server.hms_department_count = Department.search_count(domain) if domain else 0

    def _get_hms_conn(self, cache):
        """Lazily authenticate and memoize (uid, proxy) in the `cache` dict
        that _sync_model() already threads through every _prepare_vals() call
        for the run. Odoo model instances don't allow arbitrary attribute
        assignment (no plain `self._foo = ...`), so the cache dict - not the
        instance - is the only thing available to carry state across calls
        without overriding _sync_model() itself.
        """
        if "__hms_conn__" not in cache:
            cache["__hms_conn__"] = self._get_connection()
        return cache["__hms_conn__"]

    # ------------------------------------------------------------------
    # Field plan / value prep overrides
    # ------------------------------------------------------------------
    def _get_field_plan(self, uid, proxy, model):
        plan = super()._get_field_plan(uid, proxy, model)
        excluded = HMS_PLAN_EXCLUDED_FIELDS.get(model)
        if excluded:
            plan["scalar"] = [f for f in plan["scalar"] if f not in excluded]
            plan["m2o"] = {f: c for f, c in plan["m2o"].items() if f not in excluded}
            plan["m2m"] = {f: c for f, c in plan["m2m"].items() if f not in excluded}
        return plan

    def _resolve_synced_only(self, comodel, value, cache):
        """Resolve a remote many2one strictly by remote_id, never by name.

        Used for links that must never fabricate or mis-link a different
        record sharing the same name (people, companies): hms.patient's
        Related Partner and Insurance Company. Returns False if the target
        hasn't been synced yet - callers must treat that as unresolved, not
        fall through to a name search.
        """
        if not value:
            return False
        remote_id = value[0] if isinstance(value, (list, tuple)) else value
        Model = self.env[comodel]
        if "remote_id" not in Model._fields:
            return False
        key = (comodel, "synced-only", remote_id)
        if key in cache:
            return cache[key]
        rec = Model.sudo().with_context(active_test=False).search(
            [("remote_server_id", "=", self.id), ("remote_id", "=", remote_id)],
            limit=1,
        )
        cache[key] = rec.id if rec else False
        return cache[key]

    def _resolve_country(self, value, cache):
        """Resolve a remote res.country many2one via its ISO `code`, not its
        (locale-dependent) display name."""
        if not value:
            return False
        uid, proxy = self._get_hms_conn(cache)
        remote_id = value[0] if isinstance(value, (list, tuple)) else value
        key = ("res.country", "code-match", remote_id)
        if key in cache:
            return cache[key]
        code_key = ("__country_code__", remote_id)
        if code_key not in cache:
            rows = self._execute(
                uid, proxy, "res.country", "read", [[remote_id]], {"fields": ["code"]}
            )
            cache[code_key] = rows[0]["code"] if rows else False
        code = cache[code_key]
        result = False
        if code:
            country = self.env["res.country"].search([("code", "=", code)], limit=1)
            result = country.id if country else False
        cache[key] = result
        return result

    def _resolve_registration_product(self, value, cache):
        """Resolve a remote product.product to the local variant of the
        already-synced product.template (product.product itself has no
        remote_id tracking; product.template does, via product_remote_sync).
        """
        if not value:
            return False
        uid, proxy = self._get_hms_conn(cache)
        remote_product_id = value[0] if isinstance(value, (list, tuple)) else value
        key = ("registration-product", remote_product_id)
        if key in cache:
            return cache[key]
        tmpl_key = ("__remote_product_tmpl__", remote_product_id)
        if tmpl_key not in cache:
            rows = self._execute(
                uid, proxy, "product.product", "read", [[remote_product_id]],
                {"fields": ["product_tmpl_id"]},
            )
            tmpl_value = rows[0].get("product_tmpl_id") if rows else False
            cache[tmpl_key] = tmpl_value[0] if tmpl_value else False
        remote_tmpl_id = cache[tmpl_key]
        result = False
        if remote_tmpl_id:
            template = self.env["product.template"].sudo().search(
                [("remote_server_id", "=", self.id), ("remote_id", "=", remote_tmpl_id)],
                limit=1,
            )
            if template and template.product_variant_id:
                result = template.product_variant_id.id
        cache[key] = result
        return result

    def _validate_synced_partner_name(self, partner_id, context_label):
        """Refuse to build on a partner that itself has no valid name - never
        let bad upstream data (or a future regression) propagate into new
        patient/physician records."""
        partner = self.env["res.partner"].sudo().browse(partner_id)
        if not partner.name or partner.name == _("Unnamed"):
            raise UserError(
                _("%(label)s: linked partner #%(pid)s has no valid name - skipped.")
                % {"label": context_label, "pid": partner_id}
            )

    def _prepare_vals(self, model, data, plan, cache, m2m_names, o2m_commands=None):
        vals = super()._prepare_vals(model, data, plan, cache, m2m_names, o2m_commands)
        if model == "hms.patient":
            # `name` must never be written here - see the EXTRA_READ_FIELDS
            # comment above. partner_id is always an already-synced, already
            # correctly-named partner; writing through would only ever
            # overwrite good data with the base engine's "Unnamed" fallback.
            vals.pop("name", None)
            partner_id = self._resolve_synced_only("res.partner", data.get("partner_id"), cache)
            if not partner_id:
                raise UserError(
                    _("Patient '%(name)s' (remote id %(rid)s): Related Partner is not "
                      "synced locally yet - skipped.")
                    % {"name": data.get("name"), "rid": data.get("id")}
                )
            self._validate_synced_partner_name(
                partner_id,
                _("Patient (remote id %s)") % data.get("id"),
            )
            vals["partner_id"] = partner_id
            insurance_id = self._resolve_synced_only(
                "res.partner", data.get("insurance_company_id"), cache
            )
            if insurance_id:
                vals["insurance_company_id"] = insurance_id
            country_id = self._resolve_country(data.get("nationality_id"), cache)
            if country_id:
                vals["nationality_id"] = country_id
            product_id = self._resolve_registration_product(
                data.get("registration_product_id"), cache
            )
            if product_id:
                vals["registration_product_id"] = product_id
            if data.get("code"):
                vals["code"] = data["code"]
        elif model == "hms.physician":
            vals.pop("name", None)  # see EXTRA_READ_FIELDS comment - never let the "Unnamed" fallback fire
            vals["is_portal_user"] = True
            existing_physician = self.env["hms.physician"].sudo().with_context(
                active_test=False
            ).search(
                [("remote_server_id", "=", self.id), ("remote_id", "=", data["id"])], limit=1
            )
            # Reuse the already-synced partner behind this physician when one
            # exists (e.g. the doctor is also a contact/patient on the source)
            # instead of always minting a brand-new res.users + res.partner.
            partner_id = self._resolve_synced_only("res.partner", data.get("partner_id"), cache)
            if partner_id:
                self._validate_synced_partner_name(
                    partner_id,
                    _("Physician (remote id %s)") % data.get("id"),
                )
                vals["partner_id"] = partner_id
            else:
                name = data.get("name")
                if not name:
                    raise UserError(
                        _("Physician (remote id %(rid)s): remote record has no name - skipped.")
                        % {"rid": data.get("id")}
                    )
                vals["name"] = name
            login = data.get("email") or False
            if login:
                login_owner = self.env["res.users"].sudo().with_context(
                    active_test=False
                ).search([("login", "=", login)], limit=1)
                if login_owner and login_owner.id != existing_physician.user_id.id:
                    raise UserError(
                        _("Physician '%(name)s' (remote id %(rid)s): email %(email)s already "
                          "belongs to another local user (#%(uid)s) - skipped, not duplicated.")
                        % {
                            "name": data.get("name"),
                            "rid": data.get("id"),
                            "email": login,
                            "uid": login_owner.id,
                        }
                    )
            if not login:
                login = "HMS-DR-%s" % (data.get("code") or data.get("id"))
            vals["login"] = login
            if data.get("email"):
                vals["email"] = data.get("email")
        return vals

    # ------------------------------------------------------------------
    # Create / write overrides — gov_code re-validation bypass
    # ------------------------------------------------------------------
    # acs_hms's hms.patient.create()/write() call check_gov_code() when the
    # company has `unique_gov_code` enabled. check_gov_code() does
    #   self.search([('gov_code', '=', gov_code)], limit=1)
    # with NO exclusion of the record being written — so on every idempotent
    # re-sync, a patient that already stores its own gov_code matches *itself*
    # and raises a spurious ValidationError ("Patient already exists with
    # Government Identity ..."), failing the update. On create it also rejects
    # any gov_code that merely duplicates one already copied earlier in the same
    # migration, even though the source data is internally valid.
    #
    # The remote master data is the source of truth here; we must copy gov_code
    # faithfully, not re-assert local uniqueness against a partial copy. acs_hms
    # exposes the exact escape hatch for programmatic writes:
    # context flag `acs_avoid_gov_code_check`. We set it only for hms.patient
    # (the gov_code value itself is still written unchanged).
    def _safe_create(self, model, vals):
        if model == "hms.patient":
            return super(
                ProductRemoteServer,
                self.with_context(acs_avoid_gov_code_check=True),
            )._safe_create(model, vals)
        return super()._safe_create(model, vals)

    def _safe_write(self, record, vals):
        if record._name == "hms.patient":
            record = record.with_context(acs_avoid_gov_code_check=True)
        return super()._safe_write(record, vals)

    def _find_existing(self, model, data):
        if model == "hr.department":
            record = super()._find_existing(model, data)
            if record:
                return record
            return self.env[model].with_context(active_test=False).search(
                [
                    ("name", "=", data.get("name")),
                    ("company_id", "=", (self.company_id or self.env.company).id),
                ],
                limit=1,
            )
        return super()._find_existing(model, data)

    # ------------------------------------------------------------------
    # HMS lookup tables (physician.specialty, physician.degree)
    # ------------------------------------------------------------------
    def _sync_hms_lookup(self, model):
        """Create-if-missing sync for simple name-keyed lookup tables with a
        UNIQUE(name) constraint and no remote_id tracking - same posture as
        product_remote_sync's existing _sync_uom()."""
        self.ensure_one()
        uid, proxy = self._get_connection()
        Model = self.env[model].sudo()
        records = self._execute(
            uid, proxy, model, "search_read", [[]], {"fields": ["name"], "order": "id"}
        )
        created = skipped = failed = 0
        for rec in records:
            name = rec.get("name")
            if not name:
                continue
            try:
                with self.env.cr.savepoint():
                    if Model.search([("name", "=", name)], limit=1):
                        skipped += 1
                        continue
                    Model.create({"name": name})
                    created += 1
            except Exception as exc:
                failed += 1
                _logger.warning("HMS lookup sync (%s): failed for '%s': %s", model, name, exc)
        return {"created": created, "skipped": skipped, "failed": failed}

    def action_sync_hms_lookups(self):
        totals = {"created": 0, "skipped": 0, "failed": 0}
        for server in self:
            for model in HMS_LOOKUP_MODELS:
                res = server._sync_hms_lookup(model)
                for key in totals:
                    totals[key] += res[key]
        message = _(
            "HMS Lookups — Created: %(created)s | Reused: %(skipped)s | Failed: %(failed)s"
        ) % totals
        return self._notify(
            _("HMS lookup sync finished"), message, "warning" if totals["failed"] else "success"
        )

    # ------------------------------------------------------------------
    # Departments / Physicians / Patients
    # ------------------------------------------------------------------
    def action_sync_hms_departments(self):
        return self._run_sync("hr.department")

    def action_sync_hms_physicians(self):
        return self._run_sync("hms.physician")

    def action_sync_hms_physician_test_batch(self):
        self.ensure_one()
        return self._run_sync("hms.physician", limit=self.test_limit or 1)

    def action_sync_hms_patients(self):
        return self._run_sync("hms.patient")

    def action_sync_hms_patient_test_batch(self):
        self.ensure_one()
        return self._run_sync("hms.patient", limit=self.test_limit or 1)

    def _run_hms_sync(self, limit=None):
        """Run the full HMS master-data pipeline in dependency order: lookups
        -> departments -> physicians -> patients. Each _sync_model() call
        commits its own batches before the next stage starts."""
        totals = {"created": 0, "updated": 0, "failed": 0}
        lookup_totals = {"created": 0, "skipped": 0, "failed": 0}
        for server in self:
            for model in HMS_LOOKUP_MODELS:
                res = server._sync_hms_lookup(model)
                for key in lookup_totals:
                    lookup_totals[key] += res[key]
            for model in ("hr.department", "hms.physician", "hms.patient"):
                res = server._sync_model(model, limit=limit)
                for key in totals:
                    totals[key] += res[key]
        message = _(
            "HMS Lookups — Created: %(l_created)s | Reused: %(l_skipped)s | "
            "Failed: %(l_failed)s\n"
            "Departments/Physicians/Patients — Created: %(created)s | "
            "Updated: %(updated)s | Failed: %(failed)s"
        ) % {
            "l_created": lookup_totals["created"],
            "l_skipped": lookup_totals["skipped"],
            "l_failed": lookup_totals["failed"],
            "created": totals["created"],
            "updated": totals["updated"],
            "failed": totals["failed"],
        }
        return self._notify(
            _("HMS synchronization finished"),
            message,
            "warning" if (totals["failed"] or lookup_totals["failed"]) else "success",
        )

    def action_sync_hms_all(self):
        return self._run_hms_sync()

    def action_sync_hms_test_batch(self):
        self.ensure_one()
        return self._run_hms_sync(limit=self.test_limit or 1)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def action_view_hms_patients(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Synced Patients"),
            "res_model": "hms.patient",
            "view_mode": "list,form",
            "domain": [("remote_server_id", "=", self.id)],
            "context": {"create": False},
        }

    def action_view_hms_physicians(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Synced Physicians"),
            "res_model": "hms.physician",
            "view_mode": "list,form",
            "domain": [("remote_server_id", "=", self.id)],
            "context": {"create": False},
        }

    def action_view_hms_departments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Synced Departments"),
            "res_model": "hr.department",
            "view_mode": "list,form",
            "domain": [("remote_server_id", "=", self.id)],
            "context": {"create": False},
        }
