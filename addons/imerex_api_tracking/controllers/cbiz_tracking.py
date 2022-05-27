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
        #initialize variable
        cargoapi = []
        http_content = {}
        #Search parameter checking
        #if search key in the kw dictionary
        if 'search' in kw:
            #If search value is in the kw dictionary
            if kw['search']:
                api_request = request.env['cbiz.api.cargoapi'].sudo().cargo_transaction_get(kw['search'])
                if api_request[0]:
                    cargoapi = api_request
                else:
                    http_content.update({
                        "hawbnum": "No Box with given Barcode or HAWB"
                    })
        #Create Dictionary compatible with imerex_api_tracking.index template
        #Check if cargoapi has value
        if cargoapi:
            #Check if first item in list has value as cargo_transaction_get creates a list
            if cargoapi[0]:
                #update the http content for rendering of website
                http_content.update({
                    "cargoapi": cargoapi[0],
                    "hawbnum": cargoapi[0][0]['hawbnum'],
                    "searchtype": cargoapi[1]
                })
        #Return value for rendering website
        return http.request.render('imerex_api_tracking.index', http_content)