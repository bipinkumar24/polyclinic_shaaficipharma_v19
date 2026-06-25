# -*- coding: utf-8 -*-
"""One-time migration: old pharmacy_category Selection -> new
pharmacy_category_id Many2one.

Runs automatically on `-u shafic_pharmacy_reports` for any database that
had a prior version installed. Safe to run more than once (idempotent):
it only fills pharmacy_category_id where it is still NULL.

Order of operations within an Odoo update:
  1. (this is a post-migration, so the new model + fields already exist)
  2. The seed categories (data/pharmacy_category_data.xml) have been
     loaded, so pharmacy_product_category rows with matching codes exist.
  3. We map each product's old string code to the category id of the
     same code.

The old pharmacy_category column still exists at this point (the field is
intentionally retained, hidden, in this version), so reading it is safe.
"""


def migrate(cr, version):
    if not version:
        # Fresh install — nothing to migrate (defaults handle new rows).
        return

    # Guard: only proceed if both the old column and the new column exist.
    cr.execute("""
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'product_template'
           AND column_name IN ('pharmacy_category', 'pharmacy_category_id')
    """)
    cols = {r[0] for r in cr.fetchall()}
    if 'pharmacy_category' not in cols or 'pharmacy_category_id' not in cols:
        # Nothing to do / unexpected schema — fail safe by doing nothing.
        return

    # Map every product whose new field is still empty, using the old
    # string code to find the matching category. Products whose old value
    # is NULL or unknown fall back to the 'other' category.
    cr.execute("""
        UPDATE product_template pt
           SET pharmacy_category_id = c.id
          FROM pharmacy_product_category c
         WHERE c.code = pt.pharmacy_category
           AND pt.pharmacy_category_id IS NULL
    """)

    # Fallback: anything still NULL (old value was NULL or didn't match a
    # known code) goes to 'other', if that category exists.
    cr.execute("""
        UPDATE product_template pt
           SET pharmacy_category_id = c.id
          FROM pharmacy_product_category c
         WHERE c.code = 'other'
           AND pt.pharmacy_category_id IS NULL
    """)
