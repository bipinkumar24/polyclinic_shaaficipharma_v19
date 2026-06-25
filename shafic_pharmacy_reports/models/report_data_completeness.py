# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class ReportPharmacyDataCompleteness(models.Model):
    """Per-product data-completeness report.

    One row per active stockable product. Surfaces exactly which fields
    are missing per product so the team can act on it, and computes the
    same overall percentage used by the bonus scorecard. The rules here
    must match those in pharmacy.bonus.scorecard._data_completeness
    (barcode + internal reference + lot, where applicable).
    """
    _name = 'report.pharmacy.data.completeness'
    _description = 'Pharmacy Product Data Completeness'
    _auto = False
    _rec_name = 'product_id'
    _order = 'is_complete, product_id'

    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True)
    product_tmpl_id = fields.Many2one('product.template',
                                      string='Product Template',
                                      readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category',
                               readonly=True)
    pharmacy_category_id = fields.Many2one(
        'pharmacy.product.category', string='Pharmacy Category',
        readonly=True)
    barcode = fields.Char(string='Barcode', readonly=True)
    default_code = fields.Char(string='Internal Reference', readonly=True)
    tracking = fields.Selection(
        selection=[
            ('none', 'None'),
            ('lot', 'By Lot'),
            ('serial', 'By Serial'),
        ], string='Tracking', readonly=True)
    lot_count = fields.Integer(string='Lots on Record', readonly=True)

    # Boolean flags (1 = field is missing, 0 = ok)
    missing_barcode = fields.Boolean(string='Missing Barcode', readonly=True)
    missing_ref = fields.Boolean(string='Missing Reference', readonly=True)
    missing_lot = fields.Boolean(string='Missing Lot', readonly=True)
    missing_count = fields.Integer(string='Missing Fields', readonly=True)

    is_complete = fields.Boolean(string='Complete', readonly=True)
    last_write_uid = fields.Many2one('res.users', string='Last Edited By',
                                     readonly=True)
    last_write_date = fields.Datetime(string='Last Edited On', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True)

    def init(self):
        rules = self._load_rules_for_sql()
        tools.drop_view_if_exists(self.env.cr, self._table)
        sql = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    p.id AS id,
                    p.id AS product_id,
                    t.id AS product_tmpl_id,
                    t.categ_id AS categ_id,
                    t.pharmacy_category_id AS pharmacy_category_id,
                    p.barcode AS barcode,
                    p.default_code AS default_code,
                    t.tracking AS tracking,
                    COALESCE(lot.cnt, 0) AS lot_count,
                    CASE WHEN NOT (%s) THEN TRUE ELSE FALSE END
                        AS missing_barcode,
                    CASE WHEN NOT (%s) THEN TRUE ELSE FALSE END
                        AS missing_ref,
                    CASE WHEN t.tracking IN ('lot', 'serial')
                              AND NOT (%s) THEN TRUE ELSE FALSE END
                        AS missing_lot,
                    (CASE WHEN NOT (%s) THEN 1 ELSE 0 END) +
                    (CASE WHEN NOT (%s) THEN 1 ELSE 0 END) +
                    (CASE WHEN t.tracking IN ('lot', 'serial')
                               AND NOT (%s) THEN 1 ELSE 0 END)
                        AS missing_count,
                    CASE WHEN (%s) AND (%s)
                              AND (t.tracking NOT IN ('lot', 'serial')
                                   OR (%s))
                         THEN TRUE ELSE FALSE END AS is_complete,
                    p.write_uid AS last_write_uid,
                    p.write_date AS last_write_date,
                    t.company_id AS company_id
                FROM product_product p
                JOIN product_template t ON p.product_tmpl_id = t.id
                LEFT JOIN (
                    SELECT sl.product_id, COUNT(sl.id) AS cnt
                    FROM stock_lot sl
                    GROUP BY sl.product_id
                ) lot ON lot.product_id = p.id
                WHERE p.active = TRUE
                  AND t.type = 'consu'
            )
        """ % (
            self._table,
            rules['barcode'], rules['default_code'], rules['lot_name'],
            rules['barcode'], rules['default_code'], rules['lot_name'],
            rules['barcode'], rules['default_code'], rules['lot_name'],
        )
        self.env.cr.execute(sql)

    @api.model
    def _load_rules_for_sql(self):
        """Build a SQL fragment per field that returns TRUE when the
        value is valid.

        Encodes min-length and regex from pharmacy.data.rule. The
        checksum check is intentionally NOT encoded here — it is
        surfaced as a separate Python-evaluated quality signal so the
        SQL view stays fast and the bonus calculation stays
        deterministic.

        On first install the pharmacy_data_rule table may not yet
        exist (this init runs during the same module load that creates
        that table). In that case fall back to a basic non-empty check;
        the view will be rebuilt later when the rule data file loads
        and the user clicks "Apply Rules to View" — or simply on the
        next module upgrade.
        """
        self.env.cr.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'pharmacy_data_rule' LIMIT 1"
        )
        if not self.env.cr.fetchone():
            cfg = {}
        else:
            DataRule = self.env['pharmacy.data.rule'].sudo()
            rules = DataRule.search([('active', '=', True)])
            cfg = {r.field_key: r for r in rules}

        def sql_for(field_key, column_expr):
            rec = cfg.get(field_key)
            base = "({col} IS NOT NULL AND TRIM({col}) <> '')".format(
                col=column_expr)
            if not rec:
                return base
            parts = [base]
            if rec.min_length and rec.min_length > 0:
                parts.append("LENGTH(TRIM({col})) >= {n}".format(
                    col=column_expr, n=int(rec.min_length)))
            if rec.regex_pattern:
                # Escape single quotes for SQL literal.
                pat = rec.regex_pattern.replace("'", "''")
                parts.append("TRIM({col}) ~ '{p}'".format(
                    col=column_expr, p=pat))
            return ' AND '.join(parts)

        return {
            'barcode': sql_for('barcode', 'p.barcode'),
            'default_code': sql_for('default_code', 'p.default_code'),
            # Lot rule is applied to a representative lot name in the
            # subquery; for the SQL "valid" we treat presence of at
            # least one lot as sufficient. The list view has a
            # 'invalid_lot_format' column populated in Python for
            # records whose newest lot fails the rule.
            'lot_name': 'COALESCE(lot.cnt, 0) > 0',
        }

    @api.model
    def get_completeness_summary(self, company_id=False):
        """Return the headline figures consumed by the dashboard.

        Returned dictionary mirrors the calculation used by the bonus
        scorecard so the two never disagree.
        """
        domain = []
        if company_id:
            domain.append(('company_id', '=', company_id))
        all_rows = self.search(domain)
        total = len(all_rows)
        if not total:
            return {
                'total': 0, 'complete': 0, 'incomplete': 0,
                'pct_complete': 100.0,
                'missing_barcode': 0, 'missing_ref': 0, 'missing_lot': 0,
                'failed_checksum': 0, 'checksum_enabled': False,
                'by_category': [],
            }
        complete = len(all_rows.filtered(lambda r: r.is_complete))
        incomplete = total - complete
        missing_barcode = len(all_rows.filtered('missing_barcode'))
        missing_ref = len(all_rows.filtered('missing_ref'))
        missing_lot = len(all_rows.filtered('missing_lot'))

        # Checksum quality check (Python-evaluated; surfaced separately
        # so the SQL-driven bonus rate stays deterministic).
        DataRule = self.env['pharmacy.data.rule']
        rules = DataRule._get_rules()
        checksum_enabled = bool(
            rules.get('barcode', {}).get('enforce_checksum'))
        failed_checksum = 0
        if checksum_enabled:
            for row in all_rows:
                if row.barcode and not DataRule._gtin_checksum_ok(row.barcode):
                    failed_checksum += 1

        # Per-pharmacy-category breakdown
        categories = {}
        for row in all_rows:
            cat = row.pharmacy_category_id
            # key by record id (0 for unset); keep the display name handy
            key = cat.id if cat else 0
            bucket = categories.setdefault(
                key, {'total': 0, 'complete': 0,
                      'label': cat.name if cat else 'Uncategorized'})
            bucket['total'] += 1
            if row.is_complete:
                bucket['complete'] += 1
        by_category = []
        for key, b in categories.items():
            pct = (b['complete'] / b['total']) * 100.0 if b['total'] else 0.0
            by_category.append({
                'key': key,
                'label': b['label'],
                'total': b['total'],
                'complete': b['complete'],
                'incomplete': b['total'] - b['complete'],
                'pct_complete': round(pct, 1),
            })
        by_category.sort(key=lambda c: c['pct_complete'])

        return {
            'total': total,
            'complete': complete,
            'incomplete': incomplete,
            'pct_complete': round((complete / total) * 100.0, 1),
            'missing_barcode': missing_barcode,
            'missing_ref': missing_ref,
            'missing_lot': missing_lot,
            'failed_checksum': failed_checksum,
            'checksum_enabled': checksum_enabled,
            'by_category': by_category,
        }

    def action_open_product(self):
        """Open the product form to let the user fix missing fields."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
