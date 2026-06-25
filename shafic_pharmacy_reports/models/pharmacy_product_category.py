# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression


class PharmacyProductCategory(models.Model):
    """User-configurable pharmacy product category.

    Replaces the old hard-coded `pharmacy_category` Selection field. Users
    can add, rename, archive, and reorder categories from
    Configuration -> Pharmacy Categories without any code change.

    The `code` field exists for two reasons:
      1. It is the stable key used to migrate the old Selection values
         (each seeded record has a code matching an old Selection key).
      2. It lets other code refer to a category by a stable identifier
         (e.g. the prescription auto-flag) without depending on the
         display name, which users may translate or rename.
    """
    _name = 'pharmacy.product.category'
    _description = 'Pharmacy Product Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='Category Name', required=True, translate=True)
    code = fields.Char(
        string='Code',
        help='Stable internal identifier. Used for data migration and '
             'for logic that must not depend on the display name (e.g. '
             'auto-flagging prescription items). Lower-case, no spaces. '
             'Leave blank for new categories — one is generated from the '
             'name.')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    product_count = fields.Integer(
        string='Products', compute='_compute_product_count')

    _sql_constraints = [
        ('code_uniq', 'unique(code)',
         'The category code must be unique.'),
    ]

    def _compute_product_count(self):
        # Batched count grouped by category — one query for the whole set.
        if not self.ids:
            for rec in self:
                rec.product_count = 0
            return
        data = self.env['product.template']._read_group(
            [('pharmacy_category_id', 'in', self.ids)],
            groupby=['pharmacy_category_id'],
            aggregates=['__count'],
        )
        counts = {cat.id: cnt for cat, cnt in data}
        for rec in self:
            rec.product_count = counts.get(rec.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') and vals.get('name'):
                vals['code'] = self._slugify_code(vals['name'])
        return super().create(vals_list)

    def _slugify_code(self, name):
        """Generate a stable lower_snake code from a display name,
        guaranteeing uniqueness by suffixing a counter on collision."""
        base = ''.join(
            ch.lower() if ch.isalnum() else '_' for ch in (name or '')
        ).strip('_')
        while '__' in base:
            base = base.replace('__', '_')
        if not base:
            base = 'category'
        candidate = base
        n = 1
        while self.search_count([('code', '=', candidate)]):
            n += 1
            candidate = f'{base}_{n}'
        return candidate

    def action_view_products(self):
        """Open the products in this category (button on the form)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('pharmacy_category_id', '=', self.id)],
        }
