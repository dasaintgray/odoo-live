#Res Partner modification

from odoo import api, fields, models, exceptions
from odoo.tools.misc import unique
from odoo.exceptions import UserError
import json
import requests

class ResPartner(models.Model):
    """Model Res Partner."""

    _inherit = "res.partner"

    brgy = fields.Char("Barangay or Area", size=64)
    city_id = fields.Many2one("imerex_erp.city", "City Address")
    shipper_id = fields.Char("Shipper ID", size=64)
    hashrow = fields.Char("HashRow", size=64)
    _sql_constraints = [('shipper_id_unique', 'unique(shipper_id)','shipper_id must be unique!')]
    type = fields.Selection(selection_add=[('shipper','Shipper'),('consignee', 'Consignee'),('invoice',)],
            string='Address Type',
            default='contact',
            help="Used to select automatically the right address according to the context in sales and purchases documents.")

    @api.onchange("city_id")
    def onchange_city_id(self):
        """Method Onchange."""
        if self.city_id:
            self.zip = self.state_id = self.country_id = self.city = False
            self.zip = self.city_id.zip
            self.city = self.city_id.name
            state = self.city_id.state_id
            self.state_id = state.id
            if state.country_id:
                 self.country_id = state.country_id.id

    # api_headers = {
    #     "Content-Type": "application/json"
    #     }
    
    # def jwt_authentication(self):
    #     jwt_url_base = "https://jwt-clt.circuitmindz.com"
    #     jwt_url = jwt_url_base + "/api/login"
    #     jwt_body_auth = {
    #         "Username":"admin",
    #         "Password":"kQ5dcsBa98nKxfxYTK7miA=="
    #         }
    #     api_headers = {
    #         "Content-Type": "application/json"
    #         }
    #     jwt_data = json.dumps(jwt_body_auth)
    #     jwt_auth = requests.post(jwt_url, data=jwt_data, headers=api_headers)
    #     access_token = jwt_auth.json()
    #     return access_token
    
    # backend_headers = api_headers
    # access_token = jwt_authentication()
    # backend_headers["Authorization"] = 'Bearer ' + access_token
    # backend_url_base = "https://backend-clt.circuitmindz.com"
    # getshipperbyid_url = backend_url_base + "/shippers/5999"
    # getshipperbyid = requests.get(getshipperbyid_url, headers=backend_headers)
    # print(getshipperbyid.json())