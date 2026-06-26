
from odoo import api, fields, models, tools

class PosOrderReport(models.Model):
	_inherit = "report.pos.order"

	def _select(self):
		return """
			-- The purpose of this CTE is to map each "pos_order_line" to the "payment_method_id" corresponding to its "pos_order"
			-- considering we always show the first "payment_method_id"
			WITH payment_method_by_order_line AS (
				SELECT
					pol.id AS pos_order_line_id,
					(array_agg(pm.payment_method_id))[1] AS payment_method_id
				FROM pos_order_line pol
				LEFT JOIN pos_order po ON (po.id = pol.order_id)
				LEFT JOIN pos_payment pm ON (pm.pos_order_id=po.id)
				GROUP BY pol.id
			),
			first_pos_category AS (
                SELECT
                    pt.id AS product_template_id,
                    (array_agg(pc.id))[1] AS id
                FROM product_template pt
                LEFT JOIN pos_category_product_template_rel pcpt ON (pt.id = pcpt.product_template_id)
                LEFT JOIN pos_category pc ON (pcpt.pos_category_id = pc.id)
                GROUP BY pt.id
            )
			SELECT
				l.id AS id,
				1 AS nbr_lines, -- number of lines in order line is always 1
				s.date_order AS date,
				ROUND((l.price_subtotal) / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END, cu.decimal_places) AS price_subtotal_excl,
				l.qty AS product_qty,
				l.qty * l.price_unit / COALESCE(NULLIF(s.currency_rate, 0), 1.0) AS price_sub_total,

				CASE WHEN l.discount_line_type IN ('Fixed','fixed')
					THEN  ROUND((l.price_unit-l.discount) / COALESCE(NULLIF(s.currency_rate, 0), 1.0), cu.decimal_places)
					
					ELSE  ROUND((l.price_unit-l.discount) / COALESCE(NULLIF(s.currency_rate, 0), 1.0), cu.decimal_places)
				END AS price_total, 
				CASE WHEN l.discount_line_type IN ('Fixed','fixed')
					THEN  ((l.price_unit*l.qty)-(l.price_unit-l.discount)*l.qty) / COALESCE(NULLIF(s.currency_rate, 0), 1.0)
					ELSE  (l.qty * l.price_unit) * (l.discount / 100) / COALESCE(NULLIF(s.currency_rate, 0), 1.0)
				END AS total_discount, 

				CASE
					WHEN l.qty * u.factor = 0 THEN NULL
					ELSE (l.qty*l.price_unit / COALESCE(NULLIF(s.currency_rate, 0), 1.0))/(l.qty * u.factor)::decimal
				END AS average_price,
				cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT) AS delay_validation,
				s.id as order_id,
				s.partner_id AS partner_id,
				s.state AS state,
				s.user_id AS user_id,
				s.company_id AS company_id,
				s.sale_journal AS journal_id,
				l.product_id AS product_id,
				pt.categ_id AS product_categ_id,
				p.product_tmpl_id,
				ps.config_id,
				s.pricelist_id,
				s.session_id,
				s.account_move IS NOT NULL AS invoiced,
				l.price_subtotal - COALESCE(l.total_cost,0) / COALESCE(NULLIF(s.currency_rate, 0), 1.0) AS margin,
				pm.payment_method_id AS payment_method_id,
				fpc.id AS pos_categ_id
		"""

	def _group_by(self):
		return super(PosOrderReport, self)._group_by() + ", l.discount_line_type"
