#Res Partner modification

from odoo import api, fields, models
from odoo.tools.misc import unique
from odoo.exceptions import ValidationError
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
        #Validate Mobile to Be 9 digit or More
        try:
            if int(self.vat) < 999999999 and int(self.vat) > 1000000000000:
                raise ValidationError("That is not a valid IQAMA ID, IQAMA ID ranges from 10 digits to 12 digits.")
            else:
                pass
        except ValueError:
            raise ValidationError("That is not a valid IQAMA ID!!!!")          

    @api.constrains('mobile')
    def _check_mobile(self):
        #Validate Mobile to Be 9 digit or More
        try:
            if int(self.mobile):
                if len(self.mobile) < 9 or len(self.mobile) > 12:
                    raise ValidationError("That is not a valid Mobile Number")
        except ValueError:
            raise ValidationError("That is not a valid Mobile Number, Remove any special characters.")   

    @api.constrains('name_ext')
    def _check_name_ext(self):
        #Validate Max Char of Name Extension/Suffix
        if self.name_ext:
            if len(self.name_ext) > 4:
                raise ValidationError("Masyadong Mahaba Error! Max 4")

    @api.onchange("first_name", "last_name", "name_ext")
    def onchange_name(self):
        #Trigger Full Name Change onchange
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
        #Trigger Company Name Change onchange
        if not self.co_name:
            self.co_name = ""
        self.name = self.co_name
    
    @api.onchange('company_type')
    def onchange_company_type(self):
        #Changing from Individual to Company and vice versa will clean name as name for individual and Company is in a separate table column
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
        #City AddressMethod Onchange
        if self.city_id:
            self.zip = self.state_id = self.country_id = self.city = False
            self.zip = self.city_id.zip
            self.city = self.city_id.name
            state = self.city_id.state_id
            self.state_id = state.id
            if state.country_id:
                 self.country_id = state.country_id.id
   
    def write(self, vals):
        #Do not change Address/Contact Type if Shipper
        if self.shipper_id:
            try:
                if not self.type == vals['type']:
                    raise ValidationError("Already Synced as a Shipper in CircuitTrack! you cannot edit address type")
            except KeyError:
                pass

        #If no shipper_id, shipper contact will create a data in shipper service CircuitTrack
        if not self.shipper_id and self.type == 'shipper':
            sync=self.cargo_create_shippers(self)
            if sync.text:
                vals['shipper_id'] = sync.text
        #if shipper with shipper_id, will update data in shipper service CircuitTrack
        elif self.type == 'shipper':
            sync = self.cargo_update_shippers(vals)

        #reattach Odoo res_partner data and code
        partners = super(ResPartner, self).write(vals)
        return partners

    def unlink(self):
        if self.shipper_id:
            raise ValidationError("This contact cannot be deleted as it has existing data in CircuitTrack!")
        res = super(ResPartner, self).unlink()
        self.clear_caches()
        return res

    def cargo_create_shippers(self,values):
        apicargo = self.env['imerex_erp.jwt_auth'].api_headers()
        #check if in posession of JWT token
        if apicargo['token']:
            #initialize constant values
            api_body = {
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
                if values[address_fields[index]]:
                    try:
                        #for address field string type
                        api_body['shipperaddress'] += values[address_fields[index]] + ', '
                    except TypeError:
                        #for address field type with child models
                        api_body['shipperaddress'] += values[address_fields[index]].name + ', '

            #remove excess space from shipperaddress if exist
            if api_body['shipperaddress']:
                api_body['shipperaddress'] = api_body['shipperaddress'][:-2]
            
            #Remove shipperaddress entry if no value
            if not api_body['shipperaddress']:
                api_body.pop('shipperaddress')
            
            #jsonify and send api_request
            api_data = json.dumps(api_body)
            api_request = requests.post(apicargo['shipper_url'], data=api_data, headers=apicargo['headers'])
            api_response = self.api_validation(api_request)
            return api_response

    def cargo_update_shippers(self,values):
        apicargo = self.env['imerex_erp.jwt_auth'].api_headers()
        if apicargo['token']:
            #initialize constant values
            api_body = {
                "shipperId": self.shipper_id,
                "remarks": "Updated by CBIZ",
                "isactive": True,
                "countryId":3,
                "longitude": 0,
                "latitude": 0,
                "updatedBy": "Odoo",
                "auditUserId": 2,
                "shipperaddress": ""
                }
            
            #initialize fields for syncing
            cargo_fields = self.cargo_fields()
            cbiz_fields = self.cbiz_fields()
            #append api_body values
            for index in range(len(cargo_fields)):
                try:
                    if values[cbiz_fields[index]] and not cbiz_fields[index] == 'image_1920':
                        api_body[cargo_fields[index]] = values[cbiz_fields[index]]
                    elif values[cbiz_fields[index]] and cbiz_fields[index] == 'image_1920':
                        api_body[cargo_fields[index]] = 'data:image;base64,' + values[cbiz_fields[index]]
                except KeyError:
                    pass

            #Initialize updated address_fields
            address_fields = self.address_fields()
            updated_address = []
            #Get Updated Address Dict and Merge Updated Address Dict with Previous Address Dict
            for index in range(len(address_fields)):
                try:
                    if values[address_fields[index]]:
                        updated_address.append(values[address_fields[index]])
                except KeyError:
                    updated_address.append(self[address_fields[index]])

            #concatenate address for export to CircuitTrack
            for index in range(len(updated_address)):
                if updated_address[index]:
                    try:
                        api_body['shipperaddress'] += updated_address[index] + ', '
                    except TypeError:
                        #for address field type with child models
                        api_body['shipperaddress'] += updated_address[index].name + ', '

            #remove excess space from shipperaddress if exist
            if api_body['shipperaddress']:
                api_body['shipperaddress'] = api_body['shipperaddress'][:-2]
            
            #Remove shipperaddress entry if no value
            if not api_body['shipperaddress']:
                api_body.pop('shipperaddress')

            #jsonify and send api_request
            api_data = json.dumps(api_body)
            api_request = requests.patch(apicargo['shipper_url'], data=api_data, headers=apicargo['headers'])
            api_response = self.api_validation(api_request)
            return api_response

    def api_validation(self,api_request):
        if api_request.status_code == 413:
            raise ValidationError("Attachment or Image File Size Exceeded Maximum!")
        elif api_request.text == '' and api_request.request.method == 'PATCH':
            raise ValidationError("Something Went Wrong with CircuitTrack")
        elif not api_request.status_code == 200:
            raise ValidationError("Syncing Issue! Please Try Again.")
        elif api_request.text == 'Residence Number Exist':
            raise ValidationError("Shipper Residence ID Exists in CircuitTrack Database! Do your job properly")
        elif api_request.text == 'Shipper Mobile Exist':
            raise ValidationError("Shipper Mobile Number Exists in CircuitTrack Database!")
        else:
            apicargo = apicargo = self.env['imerex_erp.jwt_auth'].api_headers()
            api_refresh = requests.get(apicargo['shipper_refresh_url'],headers=apicargo['headers'])
            return api_request

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
    
