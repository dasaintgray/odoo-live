#Res Partner modification

from odoo import fields, models, api, _
from odoo.tools.misc import unique
from odoo.exceptions import ValidationError
from datetime import datetime
import json
import requests
import sys
import time
from jose import jwt
class cBizCargoJWT(models.Model):
    _description="""
    Base Class for API Integration with CargoAPI
    """
    _name='cbiz.api'
    access_token = fields.Char()
    expiration_Time = fields.Integer()
    
    def jwt_authenticate(self):
        jwt_url_base = "https://cargo-jwt.circuitmindz.com"
        jwt_url = jwt_url_base + "/api/login"
        jwt_body_auth = {
            "Username":"acctapp",
            "Password":"OdiF4cxOytm2W+TY9tRJmQ=="
            }
        api_headers = {
            "Content-Type": "application/json"
            }
        jwt_data = json.dumps(jwt_body_auth)
        jwt_request = requests.post(jwt_url, data=jwt_data, headers=api_headers)
        if jwt_request.text == 'API Authentication Failed!':
            raise ValidationError("CircuitTrack API Authentication Failed!")
        jwt_response = jwt_request.json()
        jwt_id = self.search([]).id
        if self.search([]).access_token:
            self.env.cr.execute(_("""
                DELETE FROM cbiz_api WHERE id=%s;
            """,jwt_id))
        self.env.cr.execute(_("""
            INSERT INTO cbiz_api("access_token","expiration_Time") VALUES('%s','%s');
        """,jwt_response['access_token'],jwt_response['expiration_Time']))
        token = self.search([])
        return token
    
    def api_headers(self):
        domain = 'https://cargo-gw.circuitmindz.com'
        #check expiration
        expiration = self.search([]).expiration_Time
        timenow = datetime.now().timestamp()
        if expiration < timenow:
            token = self.jwt_authenticate()
        else:
            token = self.search([])
        api_cargo = {
            'shipper_url' : domain + '/shippers/',
            'shipper_refresh_url' : domain + '/shippers-refresh/',
            'token' : token.access_token,
            'headers' : {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token.access_token
            }
        } 
        return api_cargo

    def api_validation(self,api_request):
        if api_request.text == '':
            raise ValidationError("Something Went Wrong with CircuitTrack")
        elif not api_request.status_code == 200:
            if api_request.status_code == 413:
                raise ValidationError("Attachment or Image File Size Exceeded Maximum!")
            if api_request.text == 'API Authentication Failed!':
                raise ValidationError("CircuitTrack API Authentication Failed!")
            raise ValidationError("Syncing Issue! Please Try Again.")
        elif api_request.text == 'Residence Number Exist':
            raise ValidationError("Shipper Residence ID Exists in CircuitTrack Database! Do your job properly")
        elif api_request.text == 'Shipper Mobile Exist':
            raise ValidationError("Shipper Mobile Number Exists in CircuitTrack Database!")
        else:
            apicargo = self.env['cbiz.api'].api_headers()
            requests.get(apicargo['shipper_refresh_url'],headers=apicargo['headers'])
            return api_request
        
    def api_checking(self):
        api_headers = self.api_headers()
        api_response = requests.get('https://cargo-gw.circuitmindz.com/shippers-country/3',headers=api_headers['headers'])
        api_response_cargo = requests.get('https://cargoapi1.imerex.com.ph/api/Shipper/?paramId=RGl4WnM4SGViWmkrRVBSRmhlcEZzdDh2aHkzUzlJTVRRa21sV3ZHbnpiYzZaWGZKZlBCMXA3MmRhZ0YzdzFBTE5Mb1RhRWpxdEVmdWc0SWk4bHp6dnhucXdZc1NjVWZoTXlZaWl0UUY0YVNWWmJaRWp4Q1lVcSs5UXNtSms5KytaS2tGWFZkOFdjQi9xOUdra2tUYUkxVm9rMUxaSm1qVURQbXg4Y2kyM0JnPSA=&isTable=true&isActive=false&branchbusinessunitId=1&draw=1&columns[0][data]=shipperId&columns[0][name]=&columns[0][searchable]=true&columns[0][orderable]=true&columns[0][search][value]=&columns[0][search][regex]=false&columns[1][data]=shipperName&columns[1][name]=&columns[1][searchable]=true&columns[1][orderable]=true&columns[1][search][value]=&columns[1][search][regex]=false&columns[2][data]=shipperCompany&columns[2][name]=&columns[2][searchable]=true&columns[2][orderable]=true&columns[2][search][value]=&columns[2][search][regex]=false&columns[3][data]=shipperPhoneNumber&columns[3][name]=&columns[3][searchable]=true&columns[3][orderable]=true&columns[3][search][value]=&columns[3][search][regex]=false&columns[4][data]=emailaddress&columns[4][name]=&columns[4][searchable]=true&columns[4][orderable]=true&columns[4][search][value]=&columns[4][search][regex]=false&columns[5][data]=residenceIdNumber&columns[5][name]=&columns[5][searchable]=true&columns[5][orderable]=true&columns[5][search][value]=&columns[5][search][regex]=false&columns[6][data]=6&columns[6][name]=&columns[6][searchable]=true&columns[6][orderable]=true&columns[6][search][value]=&columns[6][search][regex]=false&columns[7][data]=7&columns[7][name]=&columns[7][searchable]=false&columns[7][orderable]=false&columns[7][search][value]=&columns[7][search][regex]=false&order[0][column]=0&order[0][dir]=asc&start=0&length=1000000&search[value]=&search[regex]=false&_=1644369412700',headers={"Content-Type":"aplication/json"})
        api_data = api_response.json()
        api_data_cargo = api_response_cargo.json()
        api_elapse_time = api_response.elapsed.total_seconds()
        api_elapse_time_cargo = api_response_cargo.elapsed.total_seconds()
        api_bytes_cargo = api_response_cargo.content
        api_bytes = api_response.content
        api_length_cargo = len(api_data_cargo['data'])
        api_length = len(api_data)
        api_first_load_cargo= api_data_cargo['data'][0]
        api_first_load = api_data[0]
        api_first_load_cargo_data = sys.getsizeof(api_first_load_cargo) / (1024*1024)
        api_first_load_data = sys.getsizeof(api_first_load) / (1024*1024)
        api_cargo_data_payload = sys.getsizeof(api_bytes_cargo) / (1024*1024)
        api_data_payload = sys.getsizeof(api_bytes) / (1024*1024)
        api_length

    def sale_order_automation(self,branch_id):
        """For running only with emergency"""
        orders = self.env['sale.order'].search([("state","=",'draft'),("branch_id","=",branch_id)])
        for order in orders:
            order.action_confirm()

    def stock_move_automation(self):
        pickings = self.env['stock.picking'].search([('state','=','assigned'),('company_id','=',2)])
        for picking in pickings:
            # picking.action_assign()
            # picking.action_confirm()
            for mv in picking.move_ids_without_package:
                mv.quantity_done = mv.product_uom_qty

class cBizCargoAPI(models.Model):
    _description="""
    Cargo API
    Internal Class for Cargo Integration
    """
    _name='cbiz.api.cargoapi'

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
                "createdBy": "Odoo",
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
                "updatedBy": "Odoo",
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
            syncing = self.env['res.partner']
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
                'loyalty_id': 8800000000000 + cargo_get_shipper['shipperId'],
                'branch_id': False
            }
            create_partner = syncing.create(values)
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
