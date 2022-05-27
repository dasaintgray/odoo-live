from odoo.exceptions import ValidationError
from odoo import http, _
from odoo.http import request
import werkzeug.urls
import werkzeug.utils
import werkzeug.wrappers
from werkzeug import urls
from odoo.addons.portal.controllers.portal import pager as portal_pager

class Tracking(http.Controller):

    @http.route(['/tracking/<string:search>','/tracking'], auth='public', website=True)
    def index(self, **kw):
        api_headers = request.env['cbiz.api'].sudo().api_headers()
        cargoapi = []
        http_content = {}
        if 'search' in kw:
            if kw['search']:
                api_request = request.env['cbiz.api.cargoapi'].sudo().cargo_transaction_get(kw['search'])
                if api_request[0]:
                    cargoapi = api_request
                else:
                    http_content.update({
                        "hawbnum": "No Box with given Barcode or HAWB"
                    })
        if cargoapi:
            if cargoapi[0]:
                http_content.update({
                    "cargoapi": cargoapi[0],
                    "hawbnum": cargoapi[0][0]['hawbnum'],
                    "searchtype": cargoapi[1]
                })

        return http.request.render('imerex_api_tracking.index', http_content)