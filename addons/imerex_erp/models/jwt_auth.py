#Res Partner modification

from odoo import api, fields, models, exceptions, _
from odoo.tools.misc import unique
from odoo.exceptions import UserError
import json
import requests

class JWTAuth(models.Model):
    _name='imerex_erp.jwt_auth'
    access_token = fields.Char(size=64)
    
    def jwt_cron(self):
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
        if self.env['imerex_erp.jwt_auth'].search([]).access_token:
            self.env.cr.execute("""
                UPDATE imerex_erp_jwt_auth set access_token = '%s'
                WHERE id = 1;
            """%jwt_token['access_token'])
        else:
            self.env.cr.execute("""
                INSERT INTO imerex_erp_jwt_auth(access_token) VALUES ('%s');
            """%jwt_token['access_token'])

    # backend_headers = api_headers
    # access_token = jwt_authentication()
    # backend_headers["Authorization"] = 'Bearer ' + access_token
    # backend_url_base = "https://backend-clt.circuitmindz.com"
    # getshipperbyid_url = backend_url_base + "/shippers/5999"
    # getshipperbyid = requests.get(getshipperbyid_url, headers=backend_headers)
    # print(getshipperbyid.json())