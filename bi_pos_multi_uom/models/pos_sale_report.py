# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleReport(models.Model):
	_inherit = "sale.report"

	def _select_pos(self):
		# Inherit the native Odoo 19 POS select so every column (and its order)
		# stays identical to the Sale Order side of the UNION ALL. We only swap
		# the product_uom_qty computation to honour the multi-UOM custom_qty.
		select_ = super()._select_pos()
		return select_.replace(
			"SUM(l.qty) AS product_uom_qty",
			"SUM(CASE WHEN l.custom_qty <> l.qty THEN l.custom_qty ELSE l.qty END) AS product_uom_qty",
		)
