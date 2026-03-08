# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class CustomDashboardController(http.Controller):

    @http.route('/custom_dashboard/data', type='json', auth='user', methods=['POST'])
    def get_dashboard_data(self, date_from=None, date_to=None, **kwargs):
        return request.env['custom.dashboard'].get_dashboard_data(date_from, date_to)
