#Res Partner modification

import string
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
    loyalty_id = fields.Float("Loyalty ID",digits=[13,0])
    city_id = fields.Many2one("imerex_erp.city", "City Address")
    shipper_id = fields.Char("Shipper ID", size=64)
    hashrow = fields.Char("HashRow", size=64)
    _sql_constraints = [('shipper_id_unique', 'unique(shipper_id)','shipper_id must be unique!')]
    type = fields.Selection(selection_add=[('shipper','Shipper'),('consignee', 'Consignee'),('invoice',)],
            string='Address Type',
            default='contact',
            help="Used to select automatically the right address according to the context in sales and purchases documents.")

    # @api.constrains('vat')
    # def _check_vat(self):
    #     #Validate Mobile to Be 9 digit or More
    #     try:
    #         if int(self.vat) < 999999999 and int(self.vat) > 1000000000000:
    #             raise ValidationError("That is not a valid IQAMA ID, IQAMA ID ranges from 10 digits to 12 digits.")
    #         else:
    #             pass
    #     except ValueError:
    #         raise ValidationError("That is not a valid IQAMA ID!!!!")          

    # @api.constrains('mobile')
    # def _check_mobile(self):
    #     #Validate Mobile to Be 9 digit or More
    #     try:
    #         if int(self.mobile):
    #             if len(self.mobile) < 9 or len(self.mobile) > 12:
    #                 raise ValidationError("That is not a valid Mobile Number")
    #     except ValueError:
    #         raise ValidationError("That is not a valid Mobile Number, Remove any special characters.")   

    # @api.constrains('name_ext')
    # def _check_name_ext(self):
    #     #Validate Max Char of Name Extension/Suffix
    #     if self.name_ext:
    #         if len(self.name_ext) > 4:
    #             raise ValidationError("Masyadong Mahaba Error! Max 4")

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
            vals['loyalty_id'] = 8800000000000 + int(self.shipper_id)
            try:
                if not self.type == vals['type']:
                    raise ValidationError("Already Synced as a Shipper in CircuitTrack! you cannot edit address type")
            except KeyError:
                pass

        #If no shipper_id, shipper contact will create a data in shipper service CircuitTrack
        if not self.shipper_id and self.type == 'shipper':
            sync = self.env['cbiz.api.cargoapi'].cargo_create_shipper(self)
            if sync.text:
                vals['shipper_id'] = sync.text
                vals['loyalty_id'] = 8800000000000 + int(sync.text)

        #if shipper with shipper_id, will update data in shipper service CircuitTrack
        elif self.type == 'shipper':
            sync = self.env['cbiz.api.cargoapi'].cargo_update_shipper(vals,self)
            vals['loyalty_id'] = 8800000000000 + int(self.shipper_id)
            
        partners = super(ResPartner, self).write(vals)
        return partners

    def unlink(self):
        if self.shipper_id:
            raise ValidationError("This contact cannot be deleted as it has existing data in CircuitTrack!")
        res = super(ResPartner, self).unlink()
        self.clear_caches()
        return res
    
