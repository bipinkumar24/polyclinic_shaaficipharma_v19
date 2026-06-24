# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo import fields as odoo_fields, http, tools, _, SUPERUSER_ID
import base64

class ACSHms(http.Controller):

    @http.route(['/validate/patientradiologytest/<result_unique_code>'], type='http', auth="public", website=True, sitemap=False)
    def radiolog_result_details(self, result_unique_code, **post):
        if result_unique_code:
            result = request.env['patient.radiology.test'].sudo().search([('unique_code','=',result_unique_code)], limit=1)
            if result:
                return request.render("acs_radiology.acs_radiology_result_details", {'radiology_result': result})
        return request.render("acs_hms.acs_no_details")


class HMSPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        RadiologyTest = request.env['patient.radiology.test']
        if 'radiology_result_count' in counters:
            values['radiology_result_count'] = RadiologyTest.search_count([]) \
                if RadiologyTest.has_access('read') else 0

        RadiologyRequest = request.env['acs.radiology.request']
        if 'radiology_request_count' in counters:
            values['radiology_request_count'] = RadiologyRequest.search_count([]) \
                if RadiologyRequest.has_access('read') else 0
        return values

    #Radiology Result
    @http.route(['/my/radiology_results', '/my/radiology_results/page/<int:page>'], type='http', auth="user", website=True, sitemap=False)
    def my_radiology_results(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        RadiologyTest = request.env['patient.radiology.test']
        if not sortby:
            sortby = 'date'

        sortings = {
            'date': {'label': _('Newest'), 'order': 'date_analysis desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }

        order = sortings.get(sortby, sortings['date'])['order']
        count = RadiologyTest.search_count([])
 
        pager = portal_pager(
            url="/my/radiology_results",
            url_args={},
            total=count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected

        radiology_results = RadiologyTest.search([],
            order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'sortings': sortings,
            'sortby': sortby,
            'radiology_results': radiology_results,
            'page_name': 'radiology_result',
            'default_url': '/my/radiology_results',
            'searchbar_sortings': sortings,
            'pager': pager
        })
        return request.render("acs_radiology.radiology_results", values)

    @http.route(['/my/radiology_results/<int:result_id>'], type='http', auth="user", website=True, sitemap=False)
    def my_radiology_test_result(self, result_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('patient.radiology.test', result_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if order_sudo.attachment_ids:
            for att in order_sudo.attachment_ids:
                att._acs_portal_ensure_token()

        return request.render("acs_radiology.my_radiology_test_result", {'radiology_result': order_sudo})

    #Radiology Request
    @http.route(['/my/radiology_requests', '/my/radiology_requests/page/<int:page>'], type='http', auth="user", website=True, sitemap=False)
    def my_radiology_requests(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        RadiologyReq = request.env['acs.radiology.request']
        if not sortby:
            sortby = 'date'

        sortings = {
            'date': {'label': _('Newest'), 'order': 'date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }

        order = sortings.get(sortby, sortings['date'])['order']
        count = RadiologyReq.search_count([])
 
        pager = portal_pager(
            url="/my/radiology_requests",
            url_args={},
            total=count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        radiology_requests = RadiologyReq.search([],
            order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'sortings': sortings,
            'sortby': sortby,
            'radiology_requests': radiology_requests,
            'page_name': 'radiology_request',
            'default_url': '/my/radiology_requests',
            'searchbar_sortings': sortings,
            'pager': pager
        })
        return request.render("acs_radiology.radiology_requests", values)

    @http.route(['/my/radiology_requests/<int:radiology_request_id>'], type='http', auth="user", website=True, sitemap=False)
    def my_radiology_test_request(self, radiology_request_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('acs.radiology.request', radiology_request_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        return request.render("acs_radiology.my_radiology_test_request", {'radiology_request': order_sudo})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: