#Res Partner modification

import string
from odoo import api, fields, models
from odoo.tools.misc import unique
from odoo.exceptions import ValidationError
import json
import requests

class ChangePasswordUser(models.TransientModel):
    """ A model to configure users in the change password wizard. """
    _inherit = 'change.password.user'
    _description = 'User, Change Password Wizard'

    @api.model
    def create(self, val_list):
        check_shipper = self.env['res.users'].browse(val_list['user_id']).partner_id
        if check_shipper.type == 'shipper':
            self.env['cbiz.api.cargoapi'].cargo_password_shipper({
                'username': val_list['user_login'],
                'password': val_list['new_passwd'],
                'shipper_id': check_shipper.shipper_id
            })
        create_inherit = super(ChangePasswordUser,self).create(val_list)
        
        return create_inherit