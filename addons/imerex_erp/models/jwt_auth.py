#Res Partner modification

from odoo import fields, models
import json
import requests
import sys
from datetime import datetime
class JWTAuth(models.Model):
    _name='imerex_erp.jwt_auth'
    access_token = fields.Char()
    expiration_Time = fields.Integer()
    
    def jwt_authenticate(self):
        jwt_url_base = "https://jwt-sb-clt.circuitmindz.com"
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
        jwt_response = jwt_request.json()
        jwt_values = [
            jwt_response['access_token'],
            jwt_response['expiration_Time']
            ]
        if self.env['imerex_erp.jwt_auth'].search([]).access_token:
            self.env.cr.execute("""
                UPDATE imerex_erp_jwt_auth set "access_token" = %s, "expiration_Time" = %s WHERE id = 1;
            """,jwt_values)
        else:
            self.env.cr.execute("""
                INSERT INTO imerex_erp_jwt_auth("access_token","expiration_Time") VALUES (%s,%s);
            """,jwt_values)
        token = self.env['imerex_erp.jwt_auth'].search([])
        return token
    
    def api_headers(self):
        domain = 'https://be-sb-clt.circuitmindz.com'

        #check expiration
        expiration = self.env['imerex_erp.jwt_auth'].search([]).expiration_Time
        timenow = datetime.now().timestamp()
        if expiration < int(timenow):
            token = self.jwt_authenticate()
        else:
            token = self.env['imerex_erp.jwt_auth'].search([])
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

    def get_checking(self):
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