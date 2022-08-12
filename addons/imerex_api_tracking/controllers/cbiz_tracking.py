import base64
from re import I
from odoo.exceptions import ValidationError
from odoo import http, _

import json
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from odoo.http import request, JsonRequest, Response
import requests


class cBizTracking(Component):
    _inherit = "base.rest.service"
    _name = "cbiz.tracking.service"
    _usage = "track"
    _collection = "cbiz.services.api"
    _description = """Tracking API Service
    """

    @restapi.method(
        [(['/auth/'], "POST")],
        input_param=restapi.CerberusValidator("_validator_track"),
        # output_param=restapi.CerberusValidator("_validator_return_amendments")
        )
    def track_authentication(self, **params):
        kw = params
        if kw:
            if kw['username'] == 'imrxit':
                if kw['password'] == 'libreinumannimaster2022':
                    api_headers = self.env['cbiz.api'].sudo().api_headers()
                    return api_headers['headers']
                else:
                    raise ValidationError["WRONG PASSWORD"]
            else:
                raise ValidationError["WRONG LIFE!"]

    def _validator_track(self):
        return {
            "username": {"type": "string"},
            "password": {"type": "string"}
            }

    @restapi.method(
        [(['/<string:hawb>'], "GET")],
        )
    def track_hawb(self, hawb):
        api_cargo = self.env['cbiz.api'].sudo().api_headers()
        api_url = api_cargo['transaction_trackhawb'] + hawb
        api_headers = api_cargo['headers']
        response_url = requests.get(api_url,headers=api_headers )
        result_data = response_url.json()
        unique_qrcode = []
        return_text = ""
        for index in range(len(result_data)):
            if not result_data[index]['qrbarcode'] in unique_qrcode:
                unique_qrcode.append(result_data[index]['qrbarcode'])
                return_text += "Box QRcode:\n" + result_data[index]['qrbarcode'] + "\nStatus:\n" + result_data[index]['statusname'] + ( (" - " + result_data[index]['statusText'] )if result_data[index]['statusText'] else "" ) + "\n\n"
        if return_text == "":
            return "No HAWB #: " + hawb
        return return_text


class Tracking(http.Controller):

    @http.route(['/transaction/hawb/<string:search>'],  type='http', auth='public', method=['GET'], csrf = False, website=True)    
    def transaction_hawb(self, **kw):
        
        #Getting the search string from URI
        hawb = kw["search"]
        #Declaring Cargo 1 link address 
        return_text = request.env['sale.order'].sudo().search([('name', '=', hawb)]).name

        request._json_response = request.env['cbiz.api.cargoapi'].sudo().alternative_json_response.__get__(request, JsonRequest)
        return return_text

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
                    cargo1api = "https://cargoapi1.imerex.com.ph/api/CargoStatus/?paramId=TE05aXgzaGxhU0ZXaHBZWnJxeXNJbGJ1YWZlc250TVprMEE1NGh3WERMUWFpRTJuZGFibW92VVdQNXlNQWNYeTRTNFl6UDRDNEZGbEhWREhYYm02bWtUcnpvYWJjUkhtMnNXSnJOaFppd3VTNlkwcDhJZzVsN0tKR1lIQkhpRU4wTUJCZCt5d1FOeHRqSkpPakFtUThnZHRXM05sK0F4T0JBR0k5dDh4ZjE0PQ%3D%3D&hawb=" + kw['search']
                    cargo_details = []
                    cargo_items = ""
                    cargo1api_response = requests.get(cargo1api)
                    cargo1api_result = cargo1api_response.json()
                    if cargo1api_result:
                        for details in cargo1api_result['packageInfoDTO']:
                            cargo_items += details['packageName'] + " & "
                            
                        cargo_items = cargo_items[:len(cargo_items) - 3]
                        for details in cargo1api_result['cargo_StatusDTO']:
                            cargo_details.append({
                                'hawbnum': kw['search'],
                                'transferdate': details['processdate'],
                                'statusname': details['statusText'],
                                'statusText': cargo_items})
                        cargoapi = [
                            cargo_details,
                            'qrbarcode'
                        ]
                    if not cargoapi:
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
        return request.render('imerex_api_tracking.index', http_content)

    @http.route(['/tracking/auth'],  type='json', auth='public', method=['POST'], csrf = False, website=True)
    def track_authentication(self, **kw):
        kw_data = kw
        data = request.httprequest.data
        data_in_json = json.loads(data)
        if data_in_json:
            if data_in_json['username'] == 'imrxit':
                if data_in_json['password'] == 'libreinumannimaster2022':
                    api_headers = request.env['cbiz.api'].sudo().api_headers()
                    request._json_response = request.env['cbiz.api.cargoapi'].sudo().alternative_json_response.__get__(request, JsonRequest)
                    return api_headers['headers']
                else:
                    raise ValidationError["WRONG PASSWORD"]
            else:
                raise ValidationError["WRONG LIFE!"]

    @http.route(['/tracking/hawb/<string:search>'],  type='http', auth='public', method=['GET'], csrf = False, website=True)    
    def track_hawb(self, **kw):
        
        #Getting the search string from URI
        hawb = kw["search"]
        #Declaring Cargo 1 link address 
        cargo1api = "https://cargoapi1.imerex.com.ph/api/CargoStatus/?paramId=TE05aXgzaGxhU0ZXaHBZWnJxeXNJbGJ1YWZlc250TVprMEE1NGh3WERMUWFpRTJuZGFibW92VVdQNXlNQWNYeTRTNFl6UDRDNEZGbEhWREhYYm02bWtUcnpvYWJjUkhtMnNXSnJOaFppd3VTNlkwcDhJZzVsN0tKR1lIQkhpRU4wTUJCZCt5d1FOeHRqSkpPakFtUThnZHRXM05sK0F4T0JBR0k5dDh4ZjE0PQ%3D%3D&hawb=" + hawb
        cargo1api_response = requests.get(cargo1api)
        cargo1api_result = cargo1api_response.json()
        return_text = ""
        #Diplaying text results
        if cargo1api_result:
            return_text += "Process Date:\n" + cargo1api_result['cargo_StatusDTO'][0]['processdate'] + "\nStatus:\n" + cargo1api_result['cargo_StatusDTO'][0]['statusText'] + "\n\n"
        else:
            #Get all the API header PARAMATERS from CARGO V2 
            api_cargo = request.env['cbiz.api'].sudo().api_headers()
            api_url = api_cargo['transaction_trackhawb'] + hawb
            api_headers = api_cargo['headers']
            response_url = requests.get(api_url,headers=api_headers )
            result_data = response_url.json()
            unique_qrcode = []
            for index in range(len(result_data)):
                if not result_data[index]['qrbarcode'] in unique_qrcode:
                    unique_qrcode.append(result_data[index]['qrbarcode'])
                    return_text += "Box QRcode:\n" + result_data[index]['qrbarcode'] + "\nStatus:\n" + result_data[index]['statusname'] + ( (" - " + result_data[index]['statusText'] )if result_data[index]['statusText'] else "" ) + "\n\n"
            if return_text == "":
                return "No HAWB #: " + hawb
            else:
                domain = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                return_text += "\n" + domain  + "/tracking/?search=" + hawb
        request._json_response = request.env['cbiz.api.cargoapi'].sudo().alternative_json_response.__get__(request, JsonRequest)
        return return_text

    #@http.route(['/skedbox/<string:search>'],  type='http', auth='public', method=['POST'], csrf = False, website=True)    
    #def sked_box(self, **kw):

    @http.route(['/complaints'],  type='json', auth='public', method=['POST'], csrf = False, website=True)    
    def complaints(self, **kw):
        data = request.httprequest.data
        data_in_dict = json.loads(data)
        request.httprequest.data = ''
        request._json_response = request.env['cbiz.api.cargoapi'].sudo().alternative_json_response.__get__(request, JsonRequest)
        return []
        