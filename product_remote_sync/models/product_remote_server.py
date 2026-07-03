# -*- coding: utf-8 -*-
import logging
import xmlrpc.client

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Scalar field types copied verbatim from the remote record.
SCALAR_TYPES = {
    "char",
    "text",
    "html",
    "boolean",
    "integer",
    "float",
    "monetary",
    "date",
    "datetime",
    "selection",
    "binary",
}

# Fields that must never be synced: identity/audit columns, our own mapping
# fields, and company (kept to the local company instead of the remote one).
# Technical mixin fields (mail/activity, computed quantities, variant counters)
# are excluded automatically because they are non-stored or readonly.
EXCLUDED_FIELDS = {
    "id",
    "display_name",
    "__last_update",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
    "company_id",
    "remote_server_id",
    "remote_id",
}

# Per-model fallback "natural keys" used to match an already-synced record when
# the remote-id mapping is absent (e.g. records created before this module).
NATURAL_KEYS = {
    "product.template": ["default_code", "barcode"],
    "res.partner": ["ref", "email"],
}

# Per-model fields to never copy (unique/auto-generated identifiers that would
# collide across servers). e.g. stock.location.barcode has a per-company unique
# constraint and is auto-generated, so copying the remote value clashes.
MODEL_EXCLUDED_FIELDS = {
    "stock.location": ["barcode"],
}

# stock.lot date fields (from product_expiry) to copy from the remote lot.
LOT_DATE_FIELDS = ["expiration_date", "use_date", "removal_date", "alert_date"]

# For many2many links we create the linked record when it's missing (as the
# user requested for tags like category_id). But never auto-create these
# comodels from a bare name — it would fabricate junk / fail: they are matched
# by name only and skipped if absent.
NO_CREATE_COMODELS = {
    "res.users",
    "res.partner",
    "res.company",
    "calendar.event",
}

# many2many fields pointing at these comodels are skipped entirely: writing them
# has side effects (e.g. creating discuss.channel.member rows with required
# columns we can't supply) and they are not business data worth transferring.
M2M_SKIP_COMODELS = {
    "discuss.channel",
    "mail.channel",
    "mail.message",
    "mail.followers",
}

# Cross-version field aliases: a remote many2one whose single value is linked
# into a local many2many (the field was renamed/retyped between versions).
# e.g. v18 product.template.uom_id (m2o) -> v19 product.template.uom_ids (m2m):
# the single remote UoM is linked into the m2m.
M2O_TO_M2M_ALIASES = {
    "product.template": {"uom_id": "uom_ids"},
}

# Extra remote fields to read even though they are not in the auto plan
# (e.g. standard_price is a non-stored company-dependent field locally, but the
# remote value is needed for the packaging price conversion).
EXTRA_READ_FIELDS = {
    # barcode is non-stored on product.template (delegated to the variant) so
    # it's excluded from the auto plan, but it's needed for dedup and to sync.
    "product.template": ["standard_price", "list_price", "barcode"],
}

# Fields that cannot be changed once a record is used in posted accounting
# (e.g. account's uom_id constraint on products in posted journal entries).
# On an update conflict these are dropped so the rest of the record still
# syncs instead of failing the whole product.
UPDATE_LOCKED_FIELDS = {
    "product.template": ["uom_id", "uom_ids", "type"],
}


class ProductRemoteServer(models.Model):
    _name = "product.remote.server"
    _description = "Remote Odoo Server for Product Sync"

    name = fields.Char(string="Name", required=True)
    url = fields.Char(
        string="Server URL",
        required=True,
        help="Base URL of the remote Odoo, e.g. https://erp.example.com",
    )
    db = fields.Char(string="Database", required=True)
    username = fields.Char(string="Username", required=True)
    password = fields.Char(
        string="Password / API Key",
        required=True,
        help="Password or API key of the remote user used for the connection.",
    )
    active = fields.Boolean(default=True)
    sync_inactive = fields.Boolean(
        string="Include Archived",
        help="Also fetch archived (inactive) products from the remote server.",
    )
    test_limit = fields.Integer(
        string="Test Batch Size",
        default=20,
        help="Number of products fetched by the 'Sync Test Batch' button.",
    )
    batch_size = fields.Integer(
        string="Batch Size",
        default=100,
        help="Records fetched and created per iteration. The database is "
        "committed after each batch, so progress persists incrementally.",
    )
    stock_location_id = fields.Many2one(
        "stock.location",
        string="Stock Location",
        domain="[('usage', '=', 'internal')]",
        default=lambda self: self._default_stock_location(),
        help="Location where on-hand stock.quant records are created.",
    )

    onhand_error_log = fields.Text(
        string="On-Hand Errors", readonly=True, copy=False,
        help="Detailed list of on-hand records that failed to sync, with the "
        "reason for each, so they can be reviewed / created manually.",
    )

    def _default_stock_location(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        return warehouse.lot_stock_id.id if warehouse else False
    last_sync = fields.Datetime(string="Last Sync", readonly=True, copy=False)
    product_count = fields.Integer(
        string="Synced Products", compute="_compute_sync_counts"
    )
    partner_count = fields.Integer(
        string="Synced Partners", compute="_compute_sync_counts"
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    def _compute_sync_counts(self):
        Product = self.env["product.template"]
        Partner = self.env["res.partner"]
        for server in self:
            server.product_count = (
                Product.with_context(active_test=False).search_count(
                    [("remote_server_id", "=", server.id)]
                )
                if server.id
                else 0
            )
            server.partner_count = (
                Partner.with_context(active_test=False).search_count(
                    [("remote_server_id", "=", server.id)]
                )
                if server.id
                else 0
            )

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def _get_connection(self):
        """Authenticate against the remote server and return (uid, object_proxy)."""
        self.ensure_one()
        url = (self.url or "").strip().rstrip("/")
        if not url:
            raise UserError(_("Please set the Server URL."))
        try:
            common = xmlrpc.client.ServerProxy("%s/xmlrpc/2/common" % url)
            uid = common.authenticate(self.db, self.username, self.password, {})
        except Exception as exc:
            raise UserError(
                _("Unable to reach the remote server %(url)s:\n%(err)s")
                % {"url": url, "err": exc}
            )
        if not uid:
            raise UserError(
                _("Authentication failed for user '%(user)s' on '%(db)s'.")
                % {"user": self.username, "db": self.db}
            )
        proxy = xmlrpc.client.ServerProxy("%s/xmlrpc/2/object" % url)
        return uid, proxy

    def _execute(self, uid, proxy, model, method, args, kwargs=None):
        return proxy.execute_kw(
            self.db, uid, self.password, model, method, args, kwargs or {}
        )

    def action_test_connection(self):
        self.ensure_one()
        uid, proxy = self._get_connection()
        count = self._execute(uid, proxy, "product.template", "search_count", [[]])
        return self._notify(
            _("Connection successful"),
            _("Found %s product template(s) on the remote server.") % count,
            "success",
        )

    # ------------------------------------------------------------------
    # Field mapping helpers
    # ------------------------------------------------------------------
    def _map_category(self, categ):
        """Resolve a remote category [id, name] to a local product.category id."""
        Category = self.env["product.category"]
        if not categ:
            default = self.env.ref(
                "product.product_category_all", raise_if_not_found=False
            )
            return default.id if default else Category.search([], limit=1).id
        name = categ[1] if isinstance(categ, (list, tuple)) else categ
        category = Category.search([("name", "=", name)], limit=1)
        if not category:
            category = Category.create({"name": name})
        return category.id

    def _resolve_m2o(self, field_name, comodel, value, cache):
        """Resolve a remote many2one [id, name] to a local record id.

        If the comodel is itself synced (has a remote_id), match on the exact
        remote record id first — this keeps relations faithful (e.g. a quant's
        location/branch point to the synced location/branch, not a same-named
        one). Otherwise fall back to matching by name.
        """
        if not value:
            return False
        remote_id = value[0] if isinstance(value, (list, tuple)) else None
        name = value[1] if isinstance(value, (list, tuple)) else value
        Model = self.env[comodel]
        if remote_id and "remote_id" in Model._fields:
            key = (comodel, "rid", remote_id)
            if key in cache:
                return cache[key]
            rec = Model.sudo().with_context(active_test=False).search(
                [("remote_server_id", "=", self.id), ("remote_id", "=", remote_id)],
                limit=1,
            )
            if rec:
                cache[key] = rec.id
                return rec.id
        if not name:
            return False
        key = (comodel, name)
        if key in cache:
            return cache[key]
        # categ_id is required on product.template: reuse the create-if-missing
        # helper so a product never fails for a missing category.
        if field_name == "categ_id":
            result = self._map_category(value)
        else:
            try:
                res = self.env[comodel].sudo().name_search(
                    name=name, operator="=", limit=1
                )
            except Exception:
                res = False
            result = res[0][0] if res else False
        cache[key] = result
        return result

    def _resolve_or_create(self, comodel, name, cache):
        """Find a local record by name in `comodel`, creating it if missing.

        Used for many2many links (e.g. partner tags): unlike many2one, the
        remote value maps to a *new* linked record when none exists locally.
        Creation is attempted with just the name; comodels that require more
        (e.g. res.users) simply fail the create and are skipped + logged.
        """
        if not name:
            return False
        key = (comodel, name)
        if key in cache:
            return cache[key]
        Model = self.env[comodel].sudo()
        try:
            res = Model.name_search(name=name, operator="=", limit=1)
            rid = res[0][0] if res else False
            if (
                not rid
                and "name" in Model._fields
                and comodel not in NO_CREATE_COMODELS
            ):
                rid = Model.create({"name": name}).id
        except Exception as exc:
            _logger.info(
                "Remote sync: could not resolve/create %s '%s': %s",
                comodel,
                name,
                exc,
            )
            rid = False
        cache[key] = rid
        return rid

    def _fetch_m2m_names(self, uid, proxy, plan, records):
        """Read display names for all m2m-referenced remote ids in a batch.

        Returns {(comodel, remote_id): name}. Done once per batch (one remote
        read per comodel) instead of per record.
        """
        ids_by_model = {}
        for field_name, comodel in plan["m2m"].items():
            for data in records:
                for rid in data.get(field_name) or []:
                    ids_by_model.setdefault(comodel, set()).add(rid)
        names = {}
        for comodel, ids in ids_by_model.items():
            try:
                rows = self._execute(
                    uid, proxy, comodel, "read", [list(ids)], {"fields": ["display_name"]}
                )
            except Exception as exc:
                _logger.info(
                    "Remote sync: could not read names for %s: %s", comodel, exc
                )
                continue
            for row in rows:
                names[(comodel, row["id"])] = row.get("display_name")
        return names

    def _get_field_plan(self, uid, proxy, model):
        """Build the sync plan: which fields to copy and how, by introspection.

        Only fields present on BOTH the remote and the local model are synced.
        Local field metadata drives the classification, so the result
        automatically adapts to the installed modules / Odoo version.
        """
        Model = self.env[model]
        local_fields = Model.fields_get()
        remote_fields = self._execute(
            uid, proxy, model, "fields_get", [], {"attributes": ["type"]}
        )
        plan = {"scalar": [], "m2o": {}, "m2m": {}}
        model_excluded = MODEL_EXCLUDED_FIELDS.get(model, ())
        skipped_o2m = []
        for name, meta in local_fields.items():
            if (
                name in EXCLUDED_FIELDS
                or name in model_excluded
                or name not in remote_fields
            ):
                continue
            field = Model._fields.get(name)
            # Only writable, stored, real columns: skips computed/related and
            # the mail/activity/quantity technical fields.
            if not field or not field.store or field.readonly:
                continue
            ftype = meta.get("type")
            if ftype in SCALAR_TYPES:
                plan["scalar"].append(name)
            elif ftype == "many2one":
                plan["m2o"][name] = field.comodel_name
            elif ftype == "many2many":
                if field.comodel_name in M2M_SKIP_COMODELS:
                    continue
                plan["m2m"][name] = field.comodel_name
            elif ftype == "one2many":
                # one2many are child records (contacts, banks, invoices...) that
                # need their own dedicated sync; skipped here.
                skipped_o2m.append(name)
        if skipped_o2m:
            _logger.info(
                "Remote sync (%s): skipping one2many child fields "
                "(need dedicated handling): %s",
                model,
                ", ".join(sorted(skipped_o2m)),
            )
        return plan

    def _read_fields(self, plan):
        """Remote fields to request for each record."""
        return (
            list(plan["scalar"])
            + list(plan["m2o"].keys())
            + list(plan["m2m"].keys())
        )

    def _prepare_vals(self, model, data, plan, cache, m2m_names):
        """Build target-model values from a remote record dict and the plan."""
        Model = self.env[model]
        vals = {}
        for name in plan["scalar"]:
            if name in data:
                value = data[name]
                vals[name] = value if value is not None else False
        for name, comodel in plan["m2o"].items():
            rid = self._resolve_m2o(name, comodel, data.get(name), cache)
            if rid:  # omit unresolved m2o so local defaults / required apply
                vals[name] = rid
        for name, comodel in plan["m2m"].items():
            remote_ids = data.get(name) or []
            local_ids = []
            for rid in remote_ids:
                rec_name = m2m_names.get((comodel, rid))
                local_id = self._resolve_or_create(comodel, rec_name, cache)
                if local_id:
                    local_ids.append(local_id)
            if remote_ids:  # only touch the field when the remote had values
                vals[name] = [(6, 0, local_ids)]
        # Cross-version alias: remote many2one value -> local many2many single link
        for src, dst in M2O_TO_M2M_ALIASES.get(model, {}).items():
            if dst not in Model._fields:
                continue
            value = data.get(src)
            if not value:
                continue
            local_id = self._resolve_m2o(
                src, Model._fields[dst].comodel_name, value, cache
            )
            if local_id:
                vals[dst] = [(6, 0, [local_id])]
        # Packaging-based UoM/price conversion for products (v18 -> v19):
        # the v18 product UoM is treated as a packaging. The product's real
        # uom_id becomes that packaging's reference unit (relative_uom_id) and
        # standard_price is converted from per-packaging to per-reference-unit:
        #   standard_price = remote_standard_price / packaging.relative_factor
        if model == "product.template" and data.get("uom_id"):
            packaging_id = self._resolve_m2o(
                "uom_id", "uom.uom", data.get("uom_id"), cache
            )
            if packaging_id:
                packaging = self.env["uom.uom"].browse(packaging_id)
                base_uom = packaging.relative_uom_id or packaging
                vals["uom_id"] = base_uom.id
                factor = packaging.relative_factor or 1.0
                if factor:
                    cost = data.get("standard_price")
                    if cost:
                        vals["standard_price"] = cost / factor
                    sale = data.get("list_price")
                    if sale:
                        vals["list_price"] = sale / factor
        # barcode is non-stored on product.template (not in the plan) but
        # writable; copy it explicitly so it syncs and (ref, barcode) dedup works.
        if model == "product.template" and "barcode" in data:
            vals["barcode"] = data.get("barcode") or False
        if "name" in Model._fields and not vals.get("name"):
            vals["name"] = _("Unnamed")
        # product type: drop unknown values to stay compatible across versions
        if model == "product.template" and "type" in vals and vals[
            "type"
        ] not in ("consu", "service", "combo"):
            vals.pop("type")
        # company_id is excluded from copying (kept local), but if the model
        # requires it (e.g. res.branch), default it to the local company.
        comp_field = Model._fields.get("company_id")
        if comp_field and getattr(comp_field, "required", False) and not vals.get(
            "company_id"
        ):
            vals["company_id"] = (self.company_id or self.env.company).id
        vals["remote_server_id"] = self.id
        vals["remote_id"] = data["id"]
        # Final safety: keep only fields that exist on the local model.
        return {key: value for key, value in vals.items() if key in Model._fields}

    def _safe_write(self, record, vals):
        """Write vals, retrying without update-locked fields on conflict.

        Some fields (e.g. uom_id on a product already used in posted journal
        entries) cannot be changed once the record is used in accounting.
        Rather than fail the whole record, drop those fields and write the rest.
        """
        try:
            with self.env.cr.savepoint():
                record.write(vals)
            return
        except Exception as exc:
            locked = UPDATE_LOCKED_FIELDS.get(record._name, [])
            reduced = {k: v for k, v in vals.items() if k not in locked}
            if reduced == vals:
                raise  # nothing droppable -> genuine error, handled by caller
            _logger.info(
                "Remote sync: retrying %s(%s) without locked fields %s: %s",
                record._name,
                record.id,
                [k for k in vals if k in locked],
                exc,
            )
            with self.env.cr.savepoint():
                record.write(reduced)

    def _safe_create(self, model, vals):
        """Create the record, retrying without a conflicting barcode.

        When importing a product whose barcode already exists on a different
        product (barcode is uniquely constrained), the create is retried with
        the barcode cleared so the product is still imported (and logged),
        instead of being dropped from the sync.
        """
        try:
            with self.env.cr.savepoint():
                return self.env[model].create(vals)
        except Exception as exc:
            if vals.get("barcode"):
                _logger.info(
                    "Remote sync (%s): barcode %r conflicts, importing without it: %s",
                    model,
                    vals.get("barcode"),
                    exc,
                )
                retry = dict(vals, barcode=False)
                with self.env.cr.savepoint():
                    return self.env[model].create(retry)
            raise

    def _find_existing(self, model, data):
        """Locate an already-synced record to avoid duplicates.

        Priority: our own remote-id mapping (idempotent re-sync). Then, for
        products, a record is only considered the same when BOTH the Reference
        (default_code) AND the Barcode match the same product; if they don't
        both match one product, it is imported as a new record. Other models
        use their natural keys (any one match).
        """
        Model = self.env[model].with_context(active_test=False)
        record = Model.search(
            [("remote_server_id", "=", self.id), ("remote_id", "=", data["id"])],
            limit=1,
        )
        if record:
            return record
        if model == "product.template":
            ref = data.get("default_code") or False
            barcode = data.get("barcode") or False
            if ref or barcode:
                # both must match the SAME product to be treated as a duplicate
                return Model.search(
                    [("default_code", "=", ref), ("barcode", "=", barcode)], limit=1
                )
            return Model.browse()
        for key in NATURAL_KEYS.get(model, []):
            value = data.get(key)
            if value:
                record = Model.search([(key, "=", value)], limit=1)
                if record:
                    break
        return record

    # ------------------------------------------------------------------
    # Synchronization
    # ------------------------------------------------------------------
    # -- Products --------------------------------------------------------
    def action_sync_products(self):
        return self._run_sync("product.template")

    def action_sync_one_product(self):
        """Test helper: synchronize a single product from the remote server."""
        return self._run_sync("product.template", limit=1)

    def action_sync_test_batch(self):
        """Test helper: synchronize the first `test_limit` products."""
        self.ensure_one()
        return self._run_sync("product.template", limit=self.test_limit or 1)

    # -- Partners --------------------------------------------------------
    def action_sync_partners(self):
        return self._run_sync("res.partner")

    def action_sync_one_partner(self):
        """Test helper: synchronize a single partner from the remote server."""
        return self._run_sync("res.partner", limit=1)

    def action_sync_partner_test_batch(self):
        """Test helper: synchronize the first `test_limit` partners."""
        self.ensure_one()
        return self._run_sync("res.partner", limit=self.test_limit or 1)

    # -- Units of Measure ------------------------------------------------
    def action_sync_uom(self):
        """Sync all uom.uom records from the remote (v18) to this DB (v19).

        v18 groups units under uom.category (reference + bigger/smaller with a
        `factor`); v19 dropped the category and uses a flat tree where a unit
        points to a reference via `relative_uom_id` with `relative_factor`
        (== v18 `factor_inv`). Units are matched by name and created if missing;
        existing units are reused untouched (they may be protected master data).
        """
        created = skipped = failed = 0
        for server in self:
            res = server._sync_uom()
            created += res["created"]
            skipped += res["skipped"]
            failed += res["failed"]
        message = _(
            "Units of Measure — Created: %(created)s | Reused: %(skipped)s | "
            "Failed: %(failed)s"
        ) % {"created": created, "skipped": skipped, "failed": failed}
        return self._notify(
            _("UoM synchronization finished"),
            message,
            "warning" if failed else "success",
        )

    def _sync_uom(self):
        self.ensure_one()
        uid, proxy = self._get_connection()
        UoM = self.env["uom.uom"].sudo().with_context(active_test=False)
        read_fields = ["name", "category_id", "uom_type", "factor", "factor_inv", "active"]
        domain = [] if self.sync_inactive else [("active", "=", True)]
        records = self._execute(
            uid, proxy, "uom.uom", "search_read", [domain],
            {"fields": read_fields, "order": "id"},
        )
        # Process reference units first so the others can link to them.
        records.sort(key=lambda r: 0 if r.get("uom_type") == "reference" else 1)
        category_ref = {}  # remote category id -> local reference uom.uom
        created = skipped = failed = 0
        for rec in records:
            try:
                with self.env.cr.savepoint():
                    name = rec.get("name")
                    categ = rec.get("category_id")
                    categ_id = categ[0] if categ else False
                    is_reference = rec.get("uom_type") == "reference"
                    local = UoM.search([("name", "=", name)], limit=1)
                    if local:
                        if is_reference and categ_id:
                            category_ref[categ_id] = local
                        skipped += 1
                        continue
                    vals = {"name": name, "active": rec.get("active", True)}
                    if is_reference:
                        vals["relative_factor"] = 1.0  # base unit, no reference
                    else:
                        factor = rec.get("factor") or 0.0
                        factor_inv = rec.get("factor_inv") or (
                            1.0 / factor if factor else 1.0
                        )
                        vals["relative_factor"] = factor_inv or 1.0
                        ref = category_ref.get(categ_id)
                        if ref:
                            vals["relative_uom_id"] = ref.id
                        else:
                            _logger.info(
                                "Sync UoM: no reference for '%s' (category %s); "
                                "created as a base unit",
                                name,
                                categ,
                            )
                    new_uom = UoM.create(vals)
                    if is_reference and categ_id:
                        category_ref[categ_id] = new_uom
                    created += 1
            except Exception as exc:
                failed += 1
                _logger.warning("Sync UoM: failed for '%s': %s", rec.get("name"), exc)
        self.last_sync = fields.Datetime.now()
        _logger.info(
            "Sync UoM from %s: created=%s reused=%s failed=%s",
            self.name,
            created,
            skipped,
            failed,
        )
        return {"created": created, "skipped": skipped, "failed": failed}

    # -- On-hand quantities ----------------------------------------------
    def action_sync_onhand(self):
        """Create on-hand stock.quant (+ lot) for every synced product.

        On-hand qty is read from the remote (v18) product's qty_available and
        converted to the product's base unit using the packaging relative_factor
        (qty = on_hand * relative_factor). The product is set to lot tracking,
        a lot named after its Internal Reference is created, and a quant is set
        at the configured stock location. The lot/quant UoM follows the product
        uom_id (already the packaging's relative_uom_id), as required.
        """
        created = failed = 0
        all_failures = []
        for server in self:
            res = server._sync_onhand()
            created += res["created"]
            failed += res["failed"]
            all_failures += res.get("failures", [])
        # Store a readable report of every failure so it can be reviewed and the
        # products created manually.
        if all_failures:
            lines = [
                "Product: %s (remote id %s) | Location: %s | Lot: %s | "
                "Qty: %s\n    Reason: %s"
                % (f["product"], f["remote_id"], f["location"], f["lot"],
                   f["qty"], f["error"])
                for f in all_failures
            ]
            report = "%s failed on-hand record(s):\n\n%s" % (
                len(all_failures), "\n".join(lines)
            )
        else:
            report = False
        self.onhand_error_log = report
        message = _(
            "On-hand — Quants set: %(created)s | Failed: %(failed)s"
        ) % {"created": created, "failed": failed}
        if failed:
            message += _("\nSee the 'On-Hand Errors' field for the list of failures.")
        return self._notify(
            _("On-hand synchronization finished"),
            message,
            "warning" if failed else "success",
        )

    def _sync_onhand(self, batch_size=None):
        self.ensure_one()
        batch_size = batch_size or self.batch_size or 100
        self.env.cr.commit()  # avoid idle-in-transaction during remote XML-RPC
        uid, proxy = self._get_connection()
        Product = self.env["product.template"].with_context(active_test=False)
        products = Product.search(
            [("remote_server_id", "=", self.id), ("remote_id", "!=", False)]
        )
        cache = {}
        created = failed = 0
        failures = []
        for start in range(0, len(products), batch_size):
            chunk = products[start:start + batch_size]
            tmap = {p.remote_id: p for p in chunk}
            remote_tmpl_ids = list(tmap.keys())
            self.env.cr.commit()  # commit before this batch's remote reads
            # packaging factor per template (from its UoM)
            factor_by_tmpl = {}
            for tr in self._execute(
                uid, proxy, "product.template", "read", [remote_tmpl_ids],
                {"fields": ["uom_id"]},
            ):
                pkg_id = self._resolve_m2o("uom_id", "uom.uom", tr.get("uom_id"), cache)
                pkg = self.env["uom.uom"].browse(pkg_id) if pkg_id else None
                factor_by_tmpl[tr["id"]] = (pkg.relative_factor if pkg else 1.0) or 1.0
            # actual remote quants (internal locations) for these products
            quants = self._execute(
                uid, proxy, "stock.quant", "search_read",
                [[
                    ("product_id.product_tmpl_id", "in", remote_tmpl_ids),
                    ("location_id.usage", "=", "internal"),
                ]],
                {"fields": ["product_id", "location_id", "lot_id", "quantity",
                            "branch_id"]},
            )
            # map remote variant -> remote template
            variant_ids = list({
                q["product_id"][0] for q in quants if q.get("product_id")
            })
            v2t = {}
            if variant_ids:
                for vr in self._execute(
                    uid, proxy, "product.product", "read", [variant_ids],
                    {"fields": ["product_tmpl_id"]},
                ):
                    if vr.get("product_tmpl_id"):
                        v2t[vr["id"]] = vr["product_tmpl_id"][0]
            for q in quants:
                tmpl_id = v2t.get(q["product_id"][0]) if q.get("product_id") else None
                product = tmap.get(tmpl_id)
                if not product:
                    continue
                try:
                    with self.env.cr.savepoint():
                        self._apply_remote_quant(
                            product, q, factor_by_tmpl.get(tmpl_id, 1.0),
                            cache, uid, proxy,
                        )
                        created += 1
                except Exception as exc:
                    failed += 1
                    loc = q.get("location_id")
                    lot = q.get("lot_id")
                    failures.append({
                        "product": product.default_code or product.name,
                        "remote_id": product.remote_id,
                        "location": loc[1] if loc else "",
                        "lot": lot[1] if lot else "",
                        "qty": q.get("quantity"),
                        "error": str(exc),
                    })
                    _logger.warning(
                        "On-hand quant sync failed for %s (remote quant %s): %s",
                        product.default_code or product.name,
                        q.get("id"),
                        exc,
                    )
            self.env.cr.commit()
            _logger.info(
                "On-hand sync from %s: committed at %s (quants=%s failed=%s)",
                self.name,
                start + len(chunk),
                created,
                failed,
            )
        self.last_sync = fields.Datetime.now()
        return {"created": created, "failed": failed, "failures": failures}

    def _related_plan(self, model, uid, proxy, cache):
        """Return (and cache) the introspection plan for a related model."""
        key = ("__plan__", model)
        if key not in cache:
            cache[key] = self._get_field_plan(uid, proxy, model)
        return cache[key]

    def _sync_related_record(self, model, remote_id, uid, proxy, cache, seen=None):
        """Synchronize one remote record (branch/location) as a FULL record.

        Copies all its fields (not just the name) and stores the remote-id
        mapping. For locations, the parent (location_id) is synced first so the
        hierarchy is preserved. Returns the local record.
        """
        Empty = self.env[model]
        if not remote_id:
            return Empty
        Model = self.env[model].sudo().with_context(active_test=False)
        local = Model.search(
            [("remote_server_id", "=", self.id), ("remote_id", "=", remote_id)],
            limit=1,
        )
        if local:
            return local
        seen = seen if seen is not None else set()
        if (model, remote_id) in seen:
            return Empty
        seen.add((model, remote_id))
        plan = self._related_plan(model, uid, proxy, cache)
        rows = self._execute(
            uid, proxy, model, "read", [[remote_id]],
            {"fields": self._read_fields(plan)},
        )
        if not rows:
            return Empty
        data = rows[0]
        # sync the parent location first so location_id resolves faithfully
        if model == "stock.location" and data.get("location_id"):
            self._sync_related_record(
                "stock.location", data["location_id"][0], uid, proxy, cache, seen
            )
        vals = self._prepare_vals(model, data, plan, cache, {})
        return Model.create(vals)

    def _remote_warehouse_map(self, uid, proxy, cache):
        """Cache {lot_stock complete_name: warehouse dict} from the remote."""
        key = "__warehouses__"
        if key not in cache:
            mapping = {}
            for wh in self._execute(
                uid, proxy, "stock.warehouse", "search_read", [[]],
                {"fields": ["name", "code", "lot_stock_id"]},
            ):
                if wh.get("lot_stock_id"):
                    mapping[wh["lot_stock_id"][1]] = wh
            cache[key] = mapping
        return cache[key]

    def _resolve_quant_location(self, location_value, uid, proxy, cache):
        """Resolve a remote quant location to a local one that counts as on-hand.

        If the remote location is a warehouse's stock location, ensure the local
        warehouse exists (creating it puts the stock location under a warehouse
        view location, so it's included in the product's On-Hand quantity).
        Otherwise fall back to a faithful full-record location sync.
        """
        warehouses = self._remote_warehouse_map(uid, proxy, cache)
        wh = warehouses.get(location_value[1])
        if wh:
            Warehouse = self.env["stock.warehouse"].sudo()
            code = (wh.get("code") or wh["name"])[:5]
            local = Warehouse.search([("code", "=", code)], limit=1) or Warehouse.search(
                [("name", "=", wh["name"])], limit=1
            )
            if not local:
                local = Warehouse.create({
                    "name": wh["name"],
                    "code": code,
                    "company_id": (self.company_id or self.env.company).id,
                })
            return local.lot_stock_id
        return self._sync_related_record(
            "stock.location", location_value[0], uid, proxy, cache
        )

    def _apply_remote_quant(self, product, q, factor, cache, uid, proxy):
        """Replicate one remote stock.quant: same location, lot, branch, qty."""
        variant = product.product_variant_id
        if not variant:
            return
        # A quant can only exist on a storable product. The remote had stock for
        # it, so make it a storable good (type=consu + is_storable) if it isn't.
        fix = {}
        if product.type != "consu":
            fix["type"] = "consu"
        if not product.is_storable:
            fix["is_storable"] = True
        if fix:
            product.write(fix)
        qty = (q.get("quantity") or 0.0) * factor
        branch = (
            self._sync_related_record(
                "res.branch", q["branch_id"][0], uid, proxy, cache
            )
            if q.get("branch_id")
            else self.env["res.branch"]
        )
        location = (
            self._resolve_quant_location(q["location_id"], uid, proxy, cache)
            if q.get("location_id")
            else self.env["stock.location"]
        )
        if not location:
            return
        lot = False
        lot_value = q.get("lot_id")
        if lot_value:
            if product.tracking not in ("lot", "serial"):
                product.tracking = "lot"
            lot = self._sync_lot(variant, lot_value, uid, proxy, cache)
        # Apply the on-hand as an inventory adjustment: `inventory_quantity_auto_apply`
        # sets the quantity AND generates the audit stock.move + stock.move.line
        # (like a manual Inventory Adjustment). We deliberately do NOT put the
        # branch in the context here: the branch module writes branch_id deep in
        # _action_done and its guard rejects a branch that isn't the (super)user's
        # — so we apply branch-free (passes the guard, creates the moves) and set
        # the branch directly afterwards.
        Quant = self.env["stock.quant"].sudo().with_context(inventory_mode=True)
        quant = Quant.search(
            [
                ("product_id", "=", variant.id),
                ("location_id", "=", location.id),
                ("lot_id", "=", lot.id if lot else False),
            ],
            limit=1,
        )
        if quant:
            quant.write({"inventory_quantity_auto_apply": qty})
        else:
            vals = {
                "product_id": variant.id,
                "location_id": location.id,
                "inventory_quantity_auto_apply": qty,
            }
            if lot:
                vals["lot_id"] = lot.id
            quant = Quant.create(vals)
        # Stamp the source branch directly (bypassing the branch module's write
        # guard) on the quant and on the adjustment move lines/moves it created.
        if branch:
            self._stamp_branch(variant, location, lot, branch)

    def _stamp_branch(self, variant, location, lot, branch):
        """Set branch_id on the quant and its adjustment move(s) via SQL.

        The branch module guards ORM writes of branch_id (blocking a branch that
        isn't the user's), so for faithful replication we set it at the database
        level. stock_move_line.branch_id is a related field (no column) and
        follows the move. Everything at one internal location shares one branch.
        """
        # Flush pending ORM writes (quant/move quantities, the account_move_id
        # link) so the raw SQL below sees them.
        self.env.flush_all()
        cr = self.env.cr
        lot_id = lot.id if lot else None
        if lot_id:
            cr.execute(
                "UPDATE stock_quant SET branch_id = %s "
                "WHERE product_id = %s AND location_id = %s AND lot_id = %s",
                (branch.id, variant.id, location.id, lot_id),
            )
        else:
            cr.execute(
                "UPDATE stock_quant SET branch_id = %s "
                "WHERE product_id = %s AND location_id = %s AND lot_id IS NULL",
                (branch.id, variant.id, location.id),
            )
        # stock moves for this product touching this location (the adjustment)
        cr.execute(
            "SELECT DISTINCT move_id FROM stock_move_line "
            "WHERE product_id = %s AND %s IN (location_id, location_dest_id)",
            (variant.id, location.id),
        )
        move_ids = tuple(r[0] for r in cr.fetchall() if r[0])
        if move_ids:
            cr.execute(
                "UPDATE stock_move SET branch_id = %s WHERE id IN %s",
                (branch.id, move_ids),
            )
            # valuation accounting entries created by those stock moves
            cr.execute(
                "SELECT account_move_id FROM stock_move "
                "WHERE account_move_id IS NOT NULL AND id IN %s",
                (move_ids,),
            )
            am_ids = tuple(r[0] for r in cr.fetchall() if r[0])
            if am_ids:
                cr.execute(
                    "UPDATE account_move SET branch_id = %s WHERE id IN %s",
                    (branch.id, am_ids),
                )
                cr.execute(
                    "UPDATE account_move_line SET branch_id = %s WHERE move_id IN %s",
                    (branch.id, am_ids),
                )
        self.env["stock.quant"].invalidate_model(["branch_id"])
        self.env["stock.move"].invalidate_model(["branch_id"])
        self.env["account.move"].invalidate_model(["branch_id"])
        self.env["account.move.line"].invalidate_model(["branch_id"])

    def _lot_date_fields(self, uid, proxy, cache):
        """Which lot date fields exist on BOTH servers and are writable locally."""
        key = "__lotdatefields__"
        if key not in cache:
            Lot = self.env["stock.lot"]
            remote = self._execute(
                uid, proxy, "stock.lot", "fields_get", [], {"attributes": ["type"]}
            )
            cache[key] = [
                f
                for f in LOT_DATE_FIELDS
                if f in Lot._fields
                and f in remote
                and Lot._fields[f].store
                and not Lot._fields[f].readonly
            ]
        return cache[key]

    def _sync_lot(self, variant, lot_value, uid, proxy, cache):
        """Find/create the lot and sync its expiration/best-before/alert dates."""
        remote_lot_id, lot_name = lot_value[0], lot_value[1]
        Lot = self.env["stock.lot"].sudo()
        lot = Lot.search(
            [("product_id", "=", variant.id), ("name", "=", lot_name)], limit=1
        )
        date_fields = self._lot_date_fields(uid, proxy, cache)
        date_vals = {}
        if date_fields:
            key = ("__lotdata__", remote_lot_id)
            if key not in cache:
                rows = self._execute(
                    uid, proxy, "stock.lot", "read", [[remote_lot_id]],
                    {"fields": date_fields},
                )
                cache[key] = rows[0] if rows else {}
            data = cache[key]
            date_vals = {f: data[f] for f in date_fields if data.get(f)}
        if lot:
            if date_vals:
                lot.write(date_vals)
        else:
            lot = Lot.create(dict(date_vals, name=lot_name, product_id=variant.id))
        return lot

    # -- Engine ----------------------------------------------------------
    def _run_sync(self, model, limit=None):
        created = updated = failed = 0
        for server in self:
            res = server._sync_model(model, limit=limit)
            created += res["created"]
            updated += res["updated"]
            failed += res["failed"]
        label = self.env[model]._description or model
        message = _(
            "%(label)s — Created: %(created)s | Updated: %(updated)s | "
            "Failed: %(failed)s"
        ) % {
            "label": label,
            "created": created,
            "updated": updated,
            "failed": failed,
        }
        return self._notify(
            _("Synchronization finished"),
            message,
            "warning" if failed else "success",
        )

    def _sync_model(self, model, batch_size=None, limit=None):
        """Fetch remote records of `model` in batches and create/update locally.

        Each batch of `batch_size` records is fetched, created/updated, and then
        committed before the next batch is fetched. Committing per batch keeps
        the transaction small, persists progress incrementally (so a timeout or
        interruption keeps everything already done), and lets very large sets
        (e.g. 11k partners) sync in many small iterations instead of one request.
        """
        self.ensure_one()
        batch_size = batch_size or self.batch_size or 100
        # Commit any pending work so the DB connection is not left idle *inside a
        # transaction* during the (slow) remote XML-RPC calls below. Some poolers
        # (e.g. DigitalOcean managed Postgres) drop idle-in-transaction
        # connections, which otherwise surfaces as "connection already closed".
        self.env.cr.commit()
        uid, proxy = self._get_connection()
        Model = self.env[model]
        plan = self._get_field_plan(uid, proxy, model)
        read_fields = self._read_fields(plan)
        for extra in EXTRA_READ_FIELDS.get(model, []):
            if extra not in read_fields:
                read_fields.append(extra)
        cache = {}  # (comodel, name) -> local id, reused across the whole sync
        domain = [] if self.sync_inactive else [("active", "=", True)]
        offset = 0
        created = updated = failed = 0
        while True:
            page_size = batch_size
            if limit:
                remaining = limit - (created + updated + failed)
                if remaining <= 0:
                    break
                page_size = min(batch_size, remaining)
            kwargs = {
                "fields": read_fields,
                "order": "id",
                "limit": page_size,
                "offset": offset,
            }
            # Commit before the remote reads so the connection is idle *outside*
            # a transaction (not killed by the pooler) during the XML-RPC calls.
            self.env.cr.commit()
            records = self._execute(
                uid, proxy, model, "search_read", [domain], kwargs
            )
            if not records:
                break
            m2m_names = self._fetch_m2m_names(uid, proxy, plan, records)
            for data in records:
                try:
                    with self.env.cr.savepoint():
                        vals = self._prepare_vals(
                            model, data, plan, cache, m2m_names
                        )
                        existing = self._find_existing(model, data)
                        if existing:
                            self._safe_write(existing, vals)
                            updated += 1
                        else:
                            self._safe_create(model, vals)
                            created += 1
                except Exception as exc:
                    failed += 1
                    _logger.warning(
                        "Remote sync (%s): failed for remote id %s (%s): %s",
                        model,
                        data.get("id"),
                        data.get("default_code")
                        or data.get("ref")
                        or data.get("name"),
                        exc,
                    )
            offset += len(records)
            # Persist this batch before fetching the next one. For a manual/UI
            # run this keeps progress even if the request later times out; for a
            # cron run it keeps the transaction small.
            self.env.cr.commit()
            _logger.info(
                "Remote sync (%s) from %s: batch committed at offset %s "
                "(created=%s updated=%s failed=%s)",
                model,
                self.name,
                offset,
                created,
                updated,
                failed,
            )
            if len(records) < batch_size:
                break
        self.last_sync = fields.Datetime.now()
        _logger.info(
            "Remote sync (%s) from %s finished: created=%s updated=%s failed=%s",
            model,
            self.name,
            created,
            updated,
            failed,
        )
        return {"created": created, "updated": updated, "failed": failed}

    @api.model
    def _cron_sync_products(self):
        """Entry point for scheduled synchronization (products and partners)."""
        for server in self.search([("active", "=", True)]):
            for model in ("product.template", "res.partner"):
                try:
                    server._sync_model(model)
                except Exception as exc:
                    _logger.exception(
                        "Scheduled %s sync failed for %s: %s",
                        model,
                        server.name,
                        exc,
                    )

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def action_view_products(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Synced Products"),
            "res_model": "product.template",
            "view_mode": "list,form",
            "domain": [("remote_server_id", "=", self.id)],
            "context": {"create": False},
        }

    def action_view_partners(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Synced Partners"),
            "res_model": "res.partner",
            "view_mode": "list,form",
            "domain": [("remote_server_id", "=", self.id)],
            "context": {"create": False},
        }

    def _notify(self, title, message, kind="info"):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": kind,
                "sticky": False,
            },
        }
