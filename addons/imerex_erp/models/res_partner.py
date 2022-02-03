#Res Partner modification

from odoo import api, fields, models, exceptions
from odoo.tools.misc import unique
from odoo.exceptions import UserError, ValidationError
import json
import requests

class ResPartner(models.Model):
    """Model Res Partner."""

    _inherit = "res.partner"

    first_name = fields.Char("First Name")
    last_name = fields.Char("Surname")
    name_ext = fields.Char("Suffix")
    co_name = fields.Char("Company Name")
    brgy = fields.Char("Barangay or Area", size=64)
    city_id = fields.Many2one("imerex_erp.city", "City Address")
    shipper_id = fields.Char("Shipper ID", size=64)
    hashrow = fields.Char("HashRow", size=64)
    _sql_constraints = [('shipper_id_unique', 'unique(shipper_id)','shipper_id must be unique!')]
    type = fields.Selection(selection_add=[('shipper','Shipper'),('consignee', 'Consignee'),('invoice',)],
            string='Address Type',
            default='contact',
            help="Used to select automatically the right address according to the context in sales and purchases documents.")

    @api.constrains('vat')
    def _check_vat(self):
        try:
            if int(self.vat) < 999999999:
                raise ValidationError("That's not a valid IQAMA ID!!!!")
            else:
                pass
        except ValueError:
            raise ValidationError("That's not a valid IQAMA ID!!!!")          

    @api.constrains('name_ext')
    def _check_name_ext(self):
        if self.name_ext:
            if len(self.name_ext) > 4:
                raise ValidationError("Masyadong Mahaba Error! Max 4")

    @api.onchange("first_name", "last_name", "name_ext")
    def onchange_name(self):
        """Trigger Full Name Change on Change"""
        if not self.first_name:
            self.first_name = ""
        if not self.last_name:
            self.last_name = ""
        if not self.name_ext:
            self.name_ext = ""
        self.name = self.first_name + " " + self.last_name
        if self.name_ext:
            self.name += " " + self.name_ext
    
    @api.onchange("co_name")
    def onchange_co_name(self):
        """Trigger Company Name Change on Change"""
        if not self.co_name:
            self.co_name = ""
        self.name = self.co_name
    
    @api.onchange('company_type')
    def onchange_company_type(self):
        self.name = ""
        if self.co_name:
            self.co_name = ""
        if self.first_name:
            self.first_name = ""
        if self.last_name:
            self.last_name = ""
        if self.name_ext:
            self.name_ext = ""

    @api.onchange("city_id")
    def onchange_city_id(self):
        """City AddressMethod Onchange."""
        if self.city_id:
            self.zip = self.state_id = self.country_id = self.city = False
            self.zip = self.city_id.zip
            self.city = self.city_id.name
            state = self.city_id.state_id
            self.state_id = state.id
            if state.country_id:
                 self.country_id = state.country_id.id

    @api.model_create_multi
    def create(self, vals_list):
        partners = super(ResPartner, self).create(vals_list)
        token = self.env['imerex_erp.jwt_auth'].search([]).access_token
        image = ""
        if token and vals_list[0]['type'] == 'shipper':
            api_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
            }
            if vals_list[0]['image_1920']:
                image = vals_list[0]['image_1920']
            api_body = {
                "shipperphoto": image, 
                "shipperFirstName": vals_list[0]['first_name'],
                "shipperLastName": vals_list[0]['last_name'],
                "shipperExt": vals_list[0]['name_ext'],
                "shipperPhoneNumber": vals_list[0]['phone'],
                "shipperMobileNo": vals_list[0]['mobile'],
                "residenceIdNumber": vals_list[0]['vat'],
                "emailaddress": vals_list[0]['email'],
                # "shipperaddress": "",
                "remarks": "Created by Odoo Accounting System",
                "isactive": True,
                "countryId":3,
                "longitude": 0,
                "latitude": 0,
                "createdBy": "Odoo",
                "auditUserId": 2
                }
            api_url = 'https://be-sb-clt.circuitmindz.com/shippers/'
            api_data = json.dumps(api_body)
            api_auth = requests.post(api_url, data=api_data, headers=api_headers)
        return partners

    # def write(self,vals):
    #     write = super(ResPartner, self).write(vals)
    #     # write['name'] = self.name
    #     return write

