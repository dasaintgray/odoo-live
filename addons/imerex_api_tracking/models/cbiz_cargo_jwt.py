#Res Partner modification

from odoo import fields, models, api, _
from odoo.tools.misc import unique
from odoo.exceptions import ValidationError
from datetime import datetime
import json
import requests
import sys

class cBizCargoJWT(models.Model):
    _name='cbiz.api'
    _description="""Base Class for API Integration with CargoAPI
    """
    access_token = fields.Char()
    expiration_Time = fields.Integer()
    
    def jwt_authenticate(self):
        jwt_url_base = self.env['ir.config_parameter'].sudo().get_param('imerex_circuittrack_jwt')
        if not jwt_url_base:
            raise ValidationError("No CircuitTrack JWT URL configured in General Settings!")
        jwt_url = jwt_url_base + "/api/login"
        jwt_body_auth = {
            "Username": self.env['ir.config_parameter'].sudo().get_param('imerex_api_username'),
            "Password": self.env['ir.config_parameter'].sudo().get_param('imerex_api_password')
            }
        if not jwt_body_auth['Username'] or not jwt_body_auth['Password']:
            raise ValidationError("No CircuitTrack Username or Password configured in General Settings!")
        api_headers = {
            "Content-Type": "application/json"
            }
        jwt_data = json.dumps(jwt_body_auth)
        jwt_request = requests.post(jwt_url, data=jwt_data, headers=api_headers)
        if jwt_request.text == 'API Authentication Failed!':
            raise ValidationError("CircuitTrack API Authentication Failed!")
        jwt_response = jwt_request.json()
        jwt_id = self.search([]).id
        if self.search([]):
            self.env.cr.execute(_("""
                DELETE FROM cbiz_api WHERE id=%s;
            """,jwt_id))
        self.env.cr.execute(_("""
            INSERT INTO cbiz_api("access_token","expiration_Time") VALUES('%s','%s');
        """,jwt_response['access_token'],jwt_response['expiration_Time']))
        token = self.search([])
        return token
    
    def api_headers(self):
        domain = self.env['ir.config_parameter'].sudo().get_param('imerex_circuittrack_gw')
        if not domain:
            raise ValidationError("No CircuitTrack Gateway Configured in General Settings")
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
            'transaction_url': domain + '/transaction-track/',
            'transaction_trackhawb': domain + '/transaction-trackhawb/',
            'token' : token.access_token,
            'headers' : {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token.access_token
            }
        }
        return api_cargo

    def api_validation(self,api_request):
        api_data= api_request.json()

        if api_data == True:
            apicargo = self.env['cbiz.api'].api_headers()
            requests.get(apicargo['shipper_refresh_url'],headers=apicargo['headers'])
            return api_request
        elif not api_data:
            raise ValidationError("Something Went Wrong with CircuitTrack")
        elif 'status' in api_data:
            if api_data['status'] == 404:
                raise ValidationError("Object Not Found")
            else:
                raise ValidationError(api_data['status'] + "Error")
        elif not api_request.status_code == 200:
            if api_request.status_code == 413:
                raise ValidationError("Attachment or Image File Size Exceeded Maximum!")
            if api_request.text == 'API Authentication Failed!':
                raise ValidationError("CircuitTrack API Authentication Failed!")
            raise ValidationError("Syncing Issue! Please Try Again.")
        elif api_data == 'Residence Number Exist':
            raise ValidationError("Shipper Residence ID Exists in CircuitTrack Database! Do your job properly")
        elif api_data == 'Shipper Mobile Exist':
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