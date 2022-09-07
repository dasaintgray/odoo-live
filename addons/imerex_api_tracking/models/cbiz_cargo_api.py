#Res Partner modification

from odoo import fields, models, api, _
from odoo.tools.misc import unique
from odoo.tools import date_utils
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.http import Response
import json
import requests

class cBizCargoAPI(models.Model):
    _name='cbiz.api.cargoapi'
    _description="""Cargo API
    Internal Class for Cargo Integration
    """
    def alternative_json_response(request, result=None, error=None):
        if error is not None:
            response = error
        if result is not None:
            response = result
        mime = 'application/json'
        body = json.dumps(response, default=date_utils.json_default)
        return Response(body, status=error and error.pop('http_status', 200) or 200,
            headers=[('Content-Type', mime), ('Content-Length', len(body))]
        )

    def cargo_transaction_get(self,qrcode):
        api_headers = self.env['cbiz.api'].api_headers()
        headers = api_headers['transaction_url'] + str(qrcode)
        api_request = requests.get(headers, headers=api_headers['headers'])
        api_type = "qrbarcode"
        if not api_request.json():
            headers = api_headers['transaction_trackhawb'] + str(qrcode)
            api_request = requests.get(headers, headers=api_headers['headers'])
            api_type = "hawb"
        response = api_request.json()
        return [response, api_type]

    def shipping_track_automation(self):
        """transaction tracking"""
        orders = self.env['sale.order'].search([("name","=",name),("state","=","draft"),("company_id","=",2)])
        for order in orders:
            order.action_confirm()

    def sale_order_package(self):
        """transaction tracking"""
        orders = self.env['sale.order'].search([("state","=","draft"),("company_id","=",2),('user_id',"=",2)], limit=200)
        for order in orders:
            order.action_confirm()

    def sale_order_automation(self,body,name):
        """Sale Order Automation"""
        
        orders = self.env['sale.order'].search([("name","=",name)])
        orders.message_post(body=body,message_type="comment", subtype_xmlid="mail.mt_comment")
        orders

    def cargo_create_shipper(self,values):
        apicargo = self.env['cbiz.api'].api_headers()
        #check if in posession of JWT token
        if apicargo['token']:
            #initialize constant values
            api_body = {
                "customertype": "shipper",
                "remarks": "Created by CBIZ",
                "isactive": True,
                "countryId":3,
                "longitude": 0,
                "latitude": 0,
                "createdBy": "CBIZ",
                "auditUserId": 2,
                "shipperaddress" : ""
                }

            #initialize fields for syncing
            cargo_fields = self.cargo_fields()
            cbiz_fields = self.cbiz_fields()

            #append api_body values
            for index in range(len(cargo_fields)):
                if values[cbiz_fields[index]] and not values[cbiz_fields[index]] == values['image_1920']:
                    api_body[cargo_fields[index]] = values[cbiz_fields[index]]
                elif values[cbiz_fields[index]] and values[cbiz_fields[index]] == values['image_1920']:
                    api_body["shipperphoto"] = 'data:image;base64,' + values['image_1920'].decode('utf-8')

            #Initialize address_fields
            address_fields = self.address_fields()

            #concatenate address for export to CircuitTrack
            for index in range(len(address_fields)):
                if address_fields[index]:
                    if not type(address_fields[index]) == 'dict':
                        api_body['shipperaddress'] += address_fields[index] + ', '
                    else:
                        #for address field type with child models
                        api_body['shipperaddress'] += address_fields[index].name + ', '

            #remove excess space from shipperaddress if exist
            if api_body['shipperaddress']:
                api_body['shipperaddress'] = api_body['shipperaddress'][:-2]
            
            #Remove shipperaddress entry if no value
            if not api_body['shipperaddress']:
                api_body.pop('shipperaddress')
            
            #jsonify and send api_request
            api_data = json.dumps(api_body)
            api_request = requests.post(apicargo['shipper_url'], data=api_data, headers=apicargo['headers'])
            api_response = self.env['cbiz.api'].api_validation(api_request)
            return api_response

    def cargo_password_shipper(self,values):
        apicargo = self.env['cbiz.api'].api_headers()
        if apicargo['token']:
            #initialize constant values
            api_body = {
                "shipperId": values['shipper_id'],
                "remarks": "Updated by CBIZ",
                "isactive": True,
                "countryId":3,
                "longitude": 0,
                "latitude": 0,
                "updatedBy": "CBIZ",
                "auditUserId": 2,
                "appusername": values['username'],
                "appuserpass": values['password']
                }
            #jsonify and send api_request
            api_data = json.dumps(api_body)
            api_request = requests.put(apicargo['shipper_url'], data=api_data, headers=apicargo['headers'])
            api_response = self.env['cbiz.api'].api_validation(api_request)
            return api_response

    def cargo_update_shipper(self,values,res_partner):
        apicargo = self.env['cbiz.api'].api_headers()
        if apicargo['token']:
            #initialize constant values
            api_body = {
                "shipperId": values['shipper_id'] if 'shipper_id' in values else res_partner.shipper_id,
                "remarks": "Updated by CBIZ",
                "isactive": True,
                "countryId":3,
                "longitude": 0,
                "latitude": 0,
                "updatedBy": "CBIZ",
                "auditUserId": 2,
                "shipperaddress": "",
                "shipperExt": ""
                }
            
            #initialize fields for syncing
            cargo_fields = self.cargo_fields()
            cbiz_fields = self.cbiz_fields()
            #append api_body values
            for index in range(len(cargo_fields)):
                if cbiz_fields[index] in values:
                    if values[cbiz_fields[index]] and not cbiz_fields[index] == 'image_1920':
                        api_body[cargo_fields[index]] = values[cbiz_fields[index]]
                    elif values[cbiz_fields[index]] and cbiz_fields[index] == 'image_1920':
                        api_body[cargo_fields[index]] = 'data:image;base64,' + values[cbiz_fields[index]]

            #Initialize updated address_fields
            address_fields = self.address_fields()
            updated_address = []
            #Get Updated Address Dict and Merge Updated Address Dict with Previous Address Dict
            for index in range(len(address_fields)):
                if address_fields[index] in values:
                    if values[address_fields[index]]:
                        updated_address.append(values[address_fields[index]])
                else:
                    updated_address.append(res_partner[address_fields[index]])

            #concatenate address for export to CircuitTrack
            for index in range(len(updated_address)):
                if updated_address[index]: 
                    if type(updated_address[index]) is str:
                        api_body['shipperaddress'] += updated_address[index] + ', '
                    elif type(updated_address[index]) is int:
                        if index == 4:
                            address = self.env['res.country.state'].search([('id','=',updated_address[index])]).name
                        if index == 5:
                            address = self.env['res.country'].search([('id','=',updated_address[index])]).name
                        api_body['shipperaddress'] += address + ', '
                    else:
                        #for address field type with child models
                        api_body['shipperaddress'] += updated_address[index].name + ', '

            #remove excess space from shipperaddress if exist
            if api_body['shipperaddress']:
                api_body['shipperaddress'] = api_body['shipperaddress'][:-2]
            
            #Remove shipperaddress entry if no value
            if not api_body['shipperaddress']:
                api_body.pop('shipperaddress')

            if not api_body['shipperExt']:
                api_body['shipperExt'] = ""

            #jsonify and send api_request
            api_data = json.dumps(api_body)
            api_request = requests.put(apicargo['shipper_url'], data=api_data, headers=apicargo['headers'])
            api_response = self.env['cbiz.api'].api_validation(api_request)
            return api_response

    def cargo_get_shipper(self,shipper_id):
        apicargo = self.env['cbiz.api'].api_headers()
        if apicargo['token']:
            api_url = apicargo['shipper_url'] + str(shipper_id)
            api_request = requests.get(api_url, headers=apicargo['headers'])
            api_response = self.env['cbiz.api'].api_validation(api_request)
            return api_response.json()

    def cargo_sync_shipper(self,shipper_id):
        check_partner = self.env['res.partner'].search([('shipper_id','=',shipper_id)])
        if check_partner:
            return_partner = check_partner
        else:
            cargo_get_shipper = self.cargo_get_shipper(shipper_id)
            if 'status' in cargo_get_shipper:
                if cargo_get_shipper['status']==404:
                    raise ValidationError('No Shipper Found in Circuit Track')
            image_1920 = ''
            if 'shipperphoto' in cargo_get_shipper:
                if cargo_get_shipper['shipperphoto']:
                    image_1920 = cargo_get_shipper['shipperphoto'][18:]

            full_name = cargo_get_shipper['shipperFirstName'] + cargo_get_shipper['shipperLastName']
            if cargo_get_shipper['shipperExt']:
                full_name += cargo_get_shipper['shipperExt']
            values = {
                'type': 'shipper',
                'image_1920': image_1920,
                'name': full_name.title(),
                'shipper_id': cargo_get_shipper['shipperId'],
                'first_name': cargo_get_shipper['shipperFirstName'].title(),
                'last_name': cargo_get_shipper['shipperLastName'].title(),
                'name_ext': cargo_get_shipper['shipperExt'] or False,
                'phone': cargo_get_shipper['shipperPhoneNumber'] or False,
                'mobile': cargo_get_shipper['shipperMobileNo'] or False,
                'vat': cargo_get_shipper['residenceIdNumber'] or False,
                'email': cargo_get_shipper['emailaddress'] or False,
                'loyalty_id': 8900000000000 + cargo_get_shipper['shipperId'],
                'branch_id': False
            }

            create_partner = self.env['res.partner'].create(values)
            if cargo_get_shipper['appusername'] and cargo_get_shipper['appuserpass']:
                #Create user from create_partner
                self.env['res.users'].create([{
                    'name': create_partner.name,
                    'login': cargo_get_shipper['appusername'] or create_partner.email,
                    'partner_id': create_partner.id,
                    'company_ids': self.env['res.company'].search([]).ids,
                    'branch_ids': self.env['res.branch'].search([]).ids,
                    'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
                    }])
                #Set the password for user with partner = create_partner
                set_password = self.env['change.password.user'].create({
                        "wizard_id": self.env['change.password.wizard'].create({}).id,
                        "user_id": create_partner.user_ids.id,
                        "user_login": cargo_get_shipper['appusername'],
                        "new_passwd": cargo_get_shipper['appuserpass']
                    })
                set_password.change_password_button()
            return_partner = create_partner
        return return_partner

    def cargo_fields(self):
        cargo_fields = [
            'shipperFirstName','shipperLastName','shipperExt','shipperPhoneNumber','shipperMobileNo',
            'residenceIdNumber','emailaddress','shipperphoto'
            ]
        return cargo_fields

    def cbiz_fields(self):
        cbiz_fields = [
            'first_name','last_name','name_ext','phone','mobile','vat','email','image_1920'
            ]
        return cbiz_fields

    def address_fields(self):
        address_fields = [
            'street','street2','brgy','city','state_id','country_id','zip'
        ]
        return address_fields
