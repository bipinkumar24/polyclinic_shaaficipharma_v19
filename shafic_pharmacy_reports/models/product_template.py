# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import sql as sql_tools


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # NEW configurable category (source of truth). Users manage the list
    # under Configuration -> Pharmacy Categories.
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category',
        string='Pharmacy Category',
        index=True,
        default=lambda self: self._default_pharmacy_category_id(),
        help='Pharmacy-specific classification used in category reports. '
             'Manage the available categories under Configuration -> '
             'Pharmacy Categories.')

    # DEPRECATED: the old hard-coded Selection. Kept (hidden from views)
    # only so the one-time migration script can read existing values and
    # map them to pharmacy_category_id. Will be removed in a future
    # version once every database has been migrated. Do not use in new
    # code — read pharmacy_category_id instead.
    pharmacy_category = fields.Selection(
        selection=[
            ('prescription', 'Prescription Medicine'),
            ('otc', 'OTC Medicine'),
            ('herbal', 'Herbal / Traditional'),
            ('supplement', 'Supplement'),
            ('personal_care', 'Personal Care / Hygiene'),
            ('mother_baby', 'Mother & Baby'),
            ('cosmetic', 'Cosmetic'),
            ('wellness', 'Wellness Product'),
            ('first_aid', 'First Aid'),
            ('consumable', 'Medical Consumable'),
            ('device', 'Medical Device'),
            ('diagnostic', 'Diagnostic'),
            ('surgical', 'Surgical'),
            ('veterinary', 'Veterinary'),
            ('other', 'Other'),
        ],
        string='Pharmacy Category (deprecated)',
        help='Deprecated. Superseded by Pharmacy Category. Retained only '
             'for data migration.')

    @api.model
    def _default_pharmacy_category_id(self):
        """Default new products to the 'other' category if it exists."""
        cat = self.env.ref(
            'shafic_pharmacy_reports.cat_other', raise_if_not_found=False)
        return cat.id if cat else False
    is_controlled_drug = fields.Boolean(
        string='Controlled Drug',
        help='If set, dispensing is tracked in the controlled drugs '
             'register.')
    requires_prescription = fields.Boolean(
        string='Requires Prescription',
        help='If set, a prescription reference is expected at POS.')
    drug_schedule = fields.Char(
        string='Drug Schedule',
        help='Regulatory schedule classification (e.g. Schedule II).')
    active_ingredient = fields.Char(string='Active Ingredient')
    storage_condition = fields.Selection(
        selection=[
            ('room', 'Room Temperature'),
            ('cool', 'Cool / Refrigerated (2-8 C)'),
            ('frozen', 'Frozen'),
        ],
        string='Storage Condition', default='room')
    reorder_min_qty = fields.Float(string='Reorder Minimum Qty')
    reorder_max_qty = fields.Float(string='Reorder Maximum Qty')

    # ------------------------------------------------------------------
    # Cost / unit-of-measure mismatch warning (prevention, layer 1)
    # ------------------------------------------------------------------
    # A recurring data problem: a product is costed per pack (e.g. a box
    # of 100) but sold per individual unit (tablet), with no conversion
    # factor. The cost then dwarfs the price, COGS explodes, and margins
    # go wildly negative. This computed warning surfaces the mismatch the
    # moment the product is opened/saved, so it's caught at setup instead
    # of weeks later on the dashboard.
    #
    # Rule (confirmed with the business): a healthy product always has
    # cost < price. So we warn when cost >= price, or when cost is
    # negative (corrupted valuation data). The trigger ratio is
    # configurable via the pharmacy.cost_warn_ratio parameter (default
    # 1.0 = warn as soon as cost reaches price).
    pharmacy_cost_warning = fields.Char(
        string='Cost Setup Warning',
        compute='_compute_pharmacy_cost_warning',
        store=False,
        help='Non-blocking warning shown when the product cost looks '
             'inconsistent with its price — usually a sign the product '
             'is costed per pack but sold per unit.')

    # Stored flag powering the "Products to Fix" worklist. Unlike the
    # live warning above, this is persisted so it can be filtered and
    # listed. It is refreshed daily by the cron (authoritative, from the
    # effective cost view) and immediately when price/cost is edited.
    pharmacy_has_cost_issue = fields.Boolean(
        string='Has Cost Issue', default=False, readonly=True, index=True)
    pharmacy_cost_issue_reason = fields.Char(
        string='Cost Issue Reason', readonly=True)

    @api.depends('list_price', 'standard_price', 'pharmacy_weighted_avg_cost')
    def _compute_pharmacy_cost_warning(self):
        param = self.env['ir.config_parameter'].sudo()
        try:
            ratio = float(param.get_param(
                'shafic_pharmacy_reports.cost_warn_ratio', 1.0))
        except (TypeError, ValueError):
            ratio = 1.0
        for tmpl in self:
            warning = ''
            # Prefer the warehouse weighted-avg (effective) cost; fall
            # back to standard_price if effective isn't available.
            cost = tmpl.pharmacy_weighted_avg_cost or tmpl.standard_price or 0.0
            price = tmpl.list_price or 0.0
            if cost < 0:
                warning = (
                    "This product has a NEGATIVE cost (%.4f), which is "
                    "always a data error — usually corrupted valuation. "
                    "Check the cost and the Warehouse-Wise Cost entry."
                ) % cost
            elif price > 0 and cost >= price * ratio:
                warning = (
                    "Cost (%.4f) is at or above the sale price (%.4f). "
                    "This usually means the product is costed per pack "
                    "(e.g. a box) but sold per unit. Set the unit of "
                    "measure to the individual unit and the pack as a "
                    "purchase UoM, or correct the cost."
                ) % (cost, price)
            tmpl.pharmacy_cost_warning = warning

    # ------------------------------------------------------------------
    # "Products to Fix" worklist flag (stored, filterable)
    # ------------------------------------------------------------------
    @api.model
    def _cost_warn_ratio(self):
        param = self.env['ir.config_parameter'].sudo()
        try:
            return float(param.get_param(
                'shafic_pharmacy_reports.cost_warn_ratio', 1.0))
        except (TypeError, ValueError):
            return 1.0

    @api.model
    def flag_cost_issues(self, template_ids=None):
        """Refresh the pharmacy_has_cost_issue flag.

        Authoritative source: the product_effective_cost view (the same
        corrected cost the reports use). A template is flagged when its
        effective cost is negative, or at/above its sale price (the
        pack-vs-unit signature). One batched query, then a grouped
        write — safe to run over the whole catalog.

        :param template_ids: optionally restrict to these templates
            (used by write() for immediate refresh on edit). When None,
            the whole sellable catalog is rechecked.
        """
        ratio = self._cost_warn_ratio()
        company_id = self.env.company.id

        # Pull effective cost + price per template (first variant wins
        # for the rare multi-variant case). The view already resolves
        # the warehouse-wise cost and the standard_price fallback, so we
        # never touch the standard_price JSONB directly here.
        where_tmpl = ''
        params = [company_id]
        if template_ids:
            where_tmpl = 'AND t.id IN %s'
            params.append(tuple(template_ids))
        self.env.cr.execute("""
            SELECT t.id,
                   MIN(pec.effective_cost) AS eff_cost,
                   t.list_price
            FROM product_template t
            JOIN product_product p ON p.product_tmpl_id = t.id
            LEFT JOIN product_effective_cost pec
                   ON pec.product_id = p.id
                  AND pec.company_id = %%s
            WHERE t.sale_ok = true %s
            GROUP BY t.id, t.list_price
        """ % where_tmpl, params)

        flagged, reasons, cleared = [], {}, []
        for tmpl_id, eff_cost, list_price in self.env.cr.fetchall():
            cost = eff_cost if eff_cost is not None else 0.0
            price = list_price or 0.0
            reason = ''
            if cost < 0:
                reason = 'Negative cost (%.4f)' % cost
            elif price > 0 and cost >= price * ratio:
                reason = 'Cost %.4f >= price %.4f' % (cost, price)
            if reason:
                flagged.append(tmpl_id)
                reasons.setdefault(reason, []).append(tmpl_id)
            else:
                cleared.append(tmpl_id)

        # Write in groups: clear the healthy ones, set each reason group.
        if cleared:
            self.browse(cleared).write({
                'pharmacy_has_cost_issue': False,
                'pharmacy_cost_issue_reason': False,
            })
        for reason, ids in reasons.items():
            self.browse(ids).write({
                'pharmacy_has_cost_issue': True,
                'pharmacy_cost_issue_reason': reason,
            })
        return len(flagged)

    @api.model
    def action_recheck_cost_issues(self):
        """Manual refresh button for the worklist (server action)."""
        count = self.flag_cost_issues()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cost Issue Recheck',
                'message': '%d product(s) currently flagged to fix.' % count,
                'type': 'success' if count == 0 else 'warning',
                'sticky': False,
            },
        }

    def write(self, vals):
        """When price or cost is edited, immediately re-evaluate this
        product's cost-issue flag so it drops off the worklist as soon
        as it's fixed (rather than waiting for the daily cron)."""
        res = super().write(vals)
        trigger_fields = {'list_price', 'standard_price'}
        flag_fields = {'pharmacy_has_cost_issue', 'pharmacy_cost_issue_reason'}
        # Avoid recursion: skip when we're only writing the flag fields.
        if trigger_fields.intersection(vals) and not flag_fields.intersection(vals):
            try:
                self.flag_cost_issues(template_ids=self.ids)
            except Exception:
                # Never let the flag refresh break a product save.
                pass
        return res

    # ------------------------------------------------------------------
    # Weighted-Avg Cost (informational, shown alongside standard Cost)
    # ------------------------------------------------------------------
    # Background: the installed Warehouse-Wise Cost module
    # (sh.warehouse.cost) writes per-warehouse costs that DO NOT update
    # the product's standard_price field. Some products show a
    # standard_price 3x or more above the real warehouse-wise cost.
    # These two fields surface the weighted-average warehouse cost
    # directly on the product form so the discrepancy is visible at a
    # glance.
    #
    # Caveat: warehouse cost is stored per-variant. This field resolves
    # to the FIRST variant of the template. For pharmacy products
    # (almost all single-variant) this is correct. Multi-variant
    # templates will show only the first variant's value.

    pharmacy_weighted_avg_cost = fields.Float(
        string='Weighted Avg Cost',
        compute='_compute_pharmacy_weighted_avg_cost',
        digits=(12, 4),
        readonly=True,
        store=False,
        help='Weighted-average cost across all warehouses, weighted by '
             'on-hand quantity. Read live from the Warehouse-Wise Cost '
             'module. Shown alongside the Cost field for diagnostic '
             'comparison — large differences may indicate a stale '
             'standard cost that has not kept up with recent receipts.')

    pharmacy_cost_source = fields.Selection(
        selection=[
            ('warehouse', 'Warehouse-Wise'),
            ('standard', 'Standard (Fallback)'),
            ('zero', 'No Data'),
        ],
        string='Cost Source',
        compute='_compute_pharmacy_weighted_avg_cost',
        readonly=True,
        store=False,
        help='Where the Weighted Avg Cost figure came from. '
             'Warehouse-Wise is the real cost from receipts; '
             'Standard is a fallback when no warehouse data exists.')

    @api.depends('product_variant_ids')
    def _compute_pharmacy_weighted_avg_cost(self):
        """Read effective cost from product_effective_cost.

        Batched query: one SQL round-trip per recordset, not per record.
        Safe to call when many product templates are loaded at once
        (e.g. the products list view).
        """
        # Default everything to safe values first
        for tmpl in self:
            tmpl.pharmacy_weighted_avg_cost = 0.0
            tmpl.pharmacy_cost_source = 'zero'

        # Defensive: skip the SQL entirely on new records (no id yet)
        # or when the product_effective_cost view doesn't exist (e.g.
        # mid-upgrade). The form view degrades gracefully to 0.0.
        if not sql_tools.table_exists(self.env.cr, 'product_effective_cost'):
            return

        variant_by_tmpl = {}
        for tmpl in self:
            if not tmpl.id:
                continue

            variant = tmpl.product_variant_ids[:1]
            if variant and variant.id:
                variant_by_tmpl[tmpl.id] = variant.id

        if not variant_by_tmpl:
            return

        company_id = self.env.company.id
        product_ids = list(variant_by_tmpl.values())
        self.env.cr.execute("""
            SELECT product_id, warehouse_cost, cost_source
              FROM product_effective_cost
             WHERE product_id IN %s
               AND company_id = %s
        """, (tuple(product_ids), company_id))
        result_by_variant = {
            row[0]: (row[1] or 0.0, row[2] or 'zero')
            for row in self.env.cr.fetchall()
        }

        for tmpl in self:
            variant_id = variant_by_tmpl.get(tmpl.id)
            if variant_id and variant_id in result_by_variant:
                wh_cost, source = result_by_variant[variant_id]
                tmpl.pharmacy_weighted_avg_cost = wh_cost
                tmpl.pharmacy_cost_source = source

    @api.onchange('pharmacy_category_id')
    def _onchange_pharmacy_category(self):
        # Auto-flag prescription requirement when the chosen category is
        # the prescription one. Uses the stable code, not the name, so a
        # rename of the category doesn't break this.
        if self.pharmacy_category_id.code == 'prescription':
            self.requires_prescription = True


class ProductProduct(models.Model):
    _inherit = 'product.product'

    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category',
        related='product_tmpl_id.pharmacy_category_id',
        store=True, readonly=True, index=True)
    is_controlled_drug = fields.Boolean(
        related='product_tmpl_id.is_controlled_drug', store=True,
        readonly=True)
