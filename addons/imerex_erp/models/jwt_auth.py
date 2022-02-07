#Res Partner modification

from odoo import fields, models
import json
import requests
from datetime import datetime
class JWTAuth(models.Model):
    _name='imerex_erp.jwt_auth'
    access_token = fields.Char(size=256)
    expiration_Time = fields.Integer(size=128)
    
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
        jwt_auth = requests.post(jwt_url, data=jwt_data, headers=api_headers)
        jwt_token = jwt_auth.json()
        jwt_values = [
            jwt_token['access_token'],
            jwt_token['expiration_Time']
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