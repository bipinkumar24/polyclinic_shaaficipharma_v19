# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class PharmacyDashboardController(http.Controller):

    @http.route('/shafic_pharmacy/dashboard_data', type='json',
                auth='user', methods=['POST'])
    def dashboard_data(self, branch_id=False, **kwargs):
        """JSON endpoint returning executive dashboard KPI data."""
        return request.env['pharmacy.dashboard'].get_dashboard_data(
            branch_id=branch_id)

    @http.route('/shafic_pharmacy/branches', type='json',
                auth='user', methods=['POST'])
    def branches(self, **kwargs):
        """JSON endpoint returning the branch list for the selector."""
        return request.env['pharmacy.dashboard'].get_branches()
