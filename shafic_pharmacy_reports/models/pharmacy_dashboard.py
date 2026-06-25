# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models


class PharmacyDashboard(models.AbstractModel):
    """Provides aggregated KPI data for the OWL executive dashboard."""
    _name = 'pharmacy.dashboard'
    _description = 'Pharmacy Executive Dashboard Data Provider'

    @api.model
    def get_dashboard_data(self, branch_id=False):
        """Return a dictionary of KPI values consumed by the OWL client.

        :param branch_id: optional pharmacy.branch id to scope the data.
        """
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)

        order_domain = [('state', 'in', ('paid', 'done', 'invoiced'))]
        if branch_id:
            order_domain.append(('branch_id', '=', branch_id))

        PosOrder = self.env['pos.order']

        # --- Today's sales -------------------------------------------------
        today_orders = PosOrder.search(order_domain + [
            ('date_order', '>=', today),
        ])
        today_sales = sum(today_orders.mapped('amount_total'))

        # --- Month-to-date sales & target ----------------------------------
        mtd_orders = PosOrder.search(order_domain + [
            ('date_order', '>=', month_start),
        ])
        mtd_sales = sum(mtd_orders.mapped('amount_total'))

        target = 0.0
        if branch_id:
            branch = self.env['pharmacy.branch'].browse(branch_id)
            target = branch.sales_target
        else:
            target = sum(self.env['pharmacy.branch'].sudo().search(
                []).mapped('sales_target'))
        target_achievement = (mtd_sales / target * 100.0) if target else 0.0

        # --- Gross profit % (margin at configured cost) ----------------
        # We value sales at each product's CONFIGURED cost-to-price ratio
        # (the product Cost field / Sales Price) applied to actual
        # revenue, instead of at the posted COGS valuation.
        #
        # Why: many products are defined in a pack UoM (e.g. Bx-100) but
        # sold per unit (tablet) with no conversion factor. Quantity-based
        # costing then multiplies a per-pack cost by a per-tablet quantity
        # and explodes COGS — that is the source of the impossible
        # negative margins. The cost/price RATIO cancels the unit
        # entirely: cost = revenue x (cost / price). So the margin is
        # correct whether a line was recorded in boxes or tablets, and it
        # also sidesteps the corrupted warehouse costs by using the
        # product's own Cost field (which for these products is sane).
        #
        # Products whose configured cost is itself unusable (zero,
        # negative, or at/above price) are EXCLUDED from both the cost and
        # the revenue base, so a handful of mis-set products can't distort
        # the percentage. Those are precisely the ones to fix on the
        # product form.
        gp_domain = [('order_id.state', 'in',
                      ('paid', 'done', 'invoiced')),
                     ('order_id.date_order', '>=', month_start)]
        if branch_id:
            gp_domain.append(('order_id.branch_id', '=', branch_id))
        lines = self.env['pos.order.line'].search(gp_domain)

        # Revenue per (product, company). Revenue is reliable currency,
        # so we never need a UoM conversion here.
        rev_by_key = {}
        for line in lines:
            product = line.product_id
            if not product:
                continue
            company_id = (line.company_id.id
                          or line.order_id.company_id.id
                          or self.env.company.id)
            key = (product.id, company_id)
            rev_by_key[key] = rev_by_key.get(key, 0.0) + line.price_subtotal

        revenue = sum(rev_by_key.values())  # total MTD sales

        # Cost = the product's MOVING-AVERAGE cost (from valuation),
        # applied as a cost/price ratio against actual revenue. The ratio
        # cancels the sale UoM, so a product costed per box but sold per
        # tablet is still valued correctly. We never use standard_price.
        EffCost = self.env['product.effective.cost']
        by_company = {}
        for (product_id, company_id) in rev_by_key:
            by_company.setdefault(company_id, []).append(product_id)
        avg_map = {}
        for cid, pids in by_company.items():
            avg = EffCost.get_moving_avg_cost(pids, cid)
            for pid in pids:
                avg_map[(pid, cid)] = avg.get(pid, 0.0)

        Product = self.env['product.product']
        costed_revenue = 0.0   # revenue of products with a usable ratio
        costed_cost = 0.0      # cost implied by the moving-average ratio
        for (product_id, company_id), rev in rev_by_key.items():
            product = Product.with_company(company_id).browse(product_id)
            price = product.list_price or 0.0
            cost = avg_map.get((product_id, company_id), 0.0) or 0.0
            # Only count products whose moving-average cost is usable.
            if price > 0 and 0.0 < cost < price:
                costed_revenue += rev
                costed_cost += rev * (cost / price)
            # else: excluded from the margin base (needs a cost fix)

        gross_profit_pct = (((costed_revenue - costed_cost)
                             / costed_revenue) * 100.0) \
            if costed_revenue else 0.0

        # --- Expiry alerts -------------------------------------------------
        expiry_domain = [('expiry_bucket', 'in', ('expired', '30', '60',
                                                  '90'))]
        if branch_id:
            expiry_domain.append(('company_id', '=',
                                  self.env.company.id))
        expiry_count = self.env['report.pharmacy.expiry'].sudo().search_count(
            expiry_domain)

        # --- Low stock alerts ----------------------------------------------
        low_stock_count = self.env['report.pharmacy.reorder'].sudo().search_count(
            [('needs_reorder', '=', True)])

        # --- Top medicines (this month) ------------------------------------
        top_products = []
        product_domain = []
        if branch_id:
            product_domain.append(('branch_id', '=', branch_id))
        groups = self.env['report.pharmacy.product.sales'].sudo().read_group(
            product_domain, ['revenue:sum', 'qty_sold:sum'],
            ['product_id'], orderby='revenue desc', limit=5)
        for g in groups:
            if g.get('product_id'):
                top_products.append({
                    'name': g['product_id'][1],
                    'revenue': g.get('revenue', 0.0),
                    'qty': g.get('qty_sold', 0.0),
                })

        # --- Insurance claims ----------------------------------------------
        claim_domain = []
        if branch_id:
            claim_domain.append(('branch_id', '=', branch_id))
        pending_claims = self.env['pharmacy.insurance.claim'].sudo().search_count(
            claim_domain + [('state', 'in', ('draft', 'submitted'))])
        claims_value = sum(self.env['pharmacy.insurance.claim'].sudo().search(
            claim_domain + [('state', 'in', ('draft', 'submitted'))]
        ).mapped('claim_amount'))

        # --- Customer count (this month) -----------------------------------
        customer_count = len(mtd_orders.mapped('partner_id'))

        # --- Average basket value ------------------------------------------
        avg_basket = (mtd_sales / len(mtd_orders)) if mtd_orders else 0.0

        # --- 7-day sales trend ---------------------------------------------
        trend = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_orders = PosOrder.search(order_domain + [
                ('date_order', '>=', day),
                ('date_order', '<', day + timedelta(days=1)),
            ])
            trend.append({
                'label': day.strftime('%a %d'),
                'value': sum(day_orders.mapped('amount_total')),
            })

        # Cost / price anomaly summary for the new tile
        anomaly_summary = self.env[
            'report.pharmacy.cost.price.anomaly'
        ].sudo().get_anomaly_summary(company_id=self.env.company.id)

        # Worst-case dead stock: dead on BOTH axes (old AND not moving).
        # Pulls from the stored Stock Movement Analysis table, which
        # is refreshed by the daily cron. Read-only summary.
        dead_stock_count = 0
        dead_stock_value = 0.0
        Movement = self.env.get('report.pharmacy.stock.movement')
        if Movement is not None:
            dead_dead_domain = [
                ('movement_class', '=', 'dead'),
                ('velocity_class', '=', 'dead'),
                ('company_id', '=', self.env.company.id),
            ]
            dead_rows = Movement.sudo().search(dead_dead_domain)
            dead_stock_count = len(dead_rows)
            dead_stock_value = sum(dead_rows.mapped('stock_value'))

        return {
            'today_sales': today_sales,
            'mtd_sales': mtd_sales,
            'sales_target': target,
            'target_achievement': target_achievement,
            'gross_profit_pct': gross_profit_pct,
            'expiry_alerts': expiry_count,
            'low_stock_alerts': low_stock_count,
            'top_products': top_products,
            'pending_claims': pending_claims,
            'pending_claims_value': claims_value,
            'customer_count': customer_count,
            'avg_basket': avg_basket,
            'sales_trend': trend,
            'anomaly_total': anomaly_summary.get('total', 0),
            'anomaly_critical': anomaly_summary.get('critical', 0),
            'anomaly_warning': anomaly_summary.get('warning', 0),
            'anomaly_review': anomaly_summary.get('review', 0),
            'dead_stock_count': dead_stock_count,
            'dead_stock_value': dead_stock_value,
            'currency_symbol': self.env.company.currency_id.symbol or '',
        }

    @api.model
    def get_branches(self):
        """Return list of branches for the dashboard branch selector."""
        branches = self.env['pharmacy.branch'].sudo().search([])
        return [{'id': b.id, 'name': b.name} for b in branches]
