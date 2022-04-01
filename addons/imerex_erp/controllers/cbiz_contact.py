import base64
from odoo.exceptions import ValidationError
from odoo import api, fields, models, tools, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
class cBizContactService(Component):
    _inherit = "base.rest.service"
    _name = "cbiz.contact.service"
    _usage = "contact"
    _collection = "cbiz.services.api"
    _description = """
        Contact API Service

        Service used to retrieve contact data
    """
    @restapi.method(
        [(['/<int:id>'], "GET")],
        output_param=restapi.CerberusValidator("_validator_return_get")
        )
    def get(self, _id):
        """
        Get Contact Information
        """
        values = self._return_contact_values(_id)
        return values

    @restapi.method(
        [(['/'], "POST")],
        input_param=restapi.CerberusValidator("_validator_create"),
        output_param=restapi.CerberusValidator("_validator_return_create")
        )
    def create(self, **params):
        """
        Create Contacts
        """
        partner = self._create_contact(params)
        return partner

    @restapi.method(
        [(['/search'], "GET")],
        input_param=restapi.CerberusValidator("_validator_search"),
        )
    def search(self, name=False, shipper_id=False, type=False):
        """
        Search Contacts by ID, Name, or Shipper_id
        """
        #Default Search IDs if no params given
        search_id =  self.env["res.partner"].search([]).ids

        #Check for name params in GET URL
        if name:
            name_search = self.env["res.partner"].search([("name","like",name)]).ids
            search_id = list(set(search_id)&set(name_search))
        
        #Check for shipper_id params in GET URL
        if shipper_id:
            shipper_id_search = self.env["res.partner"].search([("shipper_id",'=',shipper_id)]).ids
            search_id = list(set(search_id)&set(shipper_id_search))

        #Check for type params in GET URL
        if type and not type == "all":
            type_search = self.env["res.partner"].search([("type","=",type)]).ids
            search_id = list(set(search_id)&set(type_search))

        #If search_id found, bypass odoo search ORM and use odoo cursor ORM for batch lookup to database of Contact with _return_contact_list
        if search_id:
            return self._return_contact_list(search_id)
        else:
            raise ValidationError("No Contact or Users Found")

    @restapi.method(
        [(['/'], "PATCH")],
        input_param=restapi.CerberusValidator("_validator_update"),
        output_param=restapi.CerberusValidator("_validator_return_update")
        )
    def update(self,**params):
        """
        Update Contact information
        """
        partner = self._update_contact(params)
        return partner

    def _validator_return_get(self):
        res = self._validator_contact_fields()
        res.update({'is_user':{'type':'boolean'}})
        return res

    def _validator_create(self):
        res = self._validator_contact_fields()
        res.pop("id")
        res.pop("name")
        res["type"] = {
            "type": "string",
            "required": True,
            "allowed": ["shipper", "consignee", "contact"]
        }
        res["password"] = {
            "type": "string"
        }
        return res

    def _validator_return_create(self):
        res = self._validator_contact_fields()
        return res

    def _validator_search(self):
        return {
            "name": {"type": "string", "nullable": True, "empty": True},
            "shipper_id": {"type": "string", "nullable": True, "empty": True},
            "type": {
                "type": "string",
                "required": False,
                "allowed": ["consignee", "shipper", "contact"],
                }
            }

    def _validator_update(self):
        res = self._validator_contact_fields()
        #Remove unneeded validator fields
        res.pop("name")
        return res

    def _validator_return_update(self):
        res = self._validator_contact_fields()
        return res
      
    def _create_contact(self,values):
        #Initialize variables
        contact_info = {}

        #Check for password params
        if 'password' in values and 'username' not in values:
            raise ValidationError("username is required for login")
        elif 'password' not in values and 'username' in values:
            raise ValidationError("password is required for login")

        #Parse image_1920 binary data to Odoo compatible binary
        values["image_1920"] = self._trim_image(values)

        #Merge name of contact for name and display name
        values["name"] = self._merge_names(values)

        #Get Contact Fields
        contact_fields = self._contact_fields()

        #Serialize to list all contact_fields in the values parameters
        for field in contact_fields:
            if field in values:
                if field == "branch_id":
                    #default false for the branch_id contact fields
                    contact_info.update({
                    field : False
                })
                else:
                    contact_info.update({
                        field : values[field]
                    })

        #Create the partner/contact with given contact_info
        created_contact = self.env["res.partner"].create(contact_info)

        #Create Portal User
        if 'username' in values and 'password' in values:
            created_user = self._user(contact=created_contact,values=values)

        #Create a dict to be return to the API
        return_contact = self._return_contact_values(created_contact.id)
        return return_contact

    def _update_contact(self,values):
        #Initialize variables
        contact_info = {}
        update_contact = {}

        #Param Validations
        if 'id' in values and 'shipper_id' in values:
            raise("choose only one of the two parameters: 'id' or 'shipper_id")
        if 'password' in values and 'username' not in values:
            raise ValidationError("username is required for login")
        elif 'password' not in values and 'username' in values:
            raise ValidationError("password is required for login")

        #Get data if 'shipper_id' exist
        if 'shipper_id' in values:
            update_contact = self.env["res.partner"].search([("shipper_id","=",str(values['shipper_id']))])
            if not update_contact:
                created_partner = self.env['cbiz.api.cargoapi'].cargo_sync_shipper(values['shipper_id'])
                values['id'] = created_partner.id

        #Get data if 'id' exist
        if 'id' in values:
            update_contact = self.env["res.partner"].browse(values['id'])

        if not update_contact:
            raise ValidationError("No contact to update!")

        #Parse data to be compatible with system
        values["image_1920"] = self._trim_image(values)
        values["name"] = self._merge_names(values,update_contact)
        
        #Get Contact fields for serialization
        contact_fields = self._contact_fields()

        #Serialize contact_fields with values/params
        for field in contact_fields:
            if field in values:
                if field == "branch_id":
                    #contact_field branch always have False value
                    contact_info.update({
                    field : False
                    })
                else:
                    contact_info.update({
                        field : values[field]
                    })

        #Remove image key if no data inside
        if not contact_info["image_1920"]:
            contact_info.pop("image_1920")

        #update contact field
        update_contact.write(contact_info)
        #Check for logins params 
        if 'username' in values and 'password' in values:
            #If user exist, just edit password
            if update_contact.user_ids:
                update_contact.user_ids.write({
                    "login": values['username']
                })
                self._user(contact=update_contact,create=False,values=values)
            else:
                self._user(contact=update_contact,values=values)          

        return self._return_contact_values(update_contact.id)

    def _validator_contact_fields(self):
        res = {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "type": {},
            "shipper_id": {},
            "first_name": {},
            "last_name": {},
            "name_ext": {},
            "phone": {},
            "mobile": {},
            "vat": {},
            "email": {},
            "image_1920": {},
            "password": {},
            "username": {},
        }
        return res

    def _user(self,contact,create=True,values=False,):
        if create == True:
            user = self.env['res.users'].create([{
                'name': contact.name,
                'login': values['username'] or contact.email,
                'partner_id': contact.id,
                'company_ids': self.env['res.company'].search([]).ids,
                'branch_ids': self.env['res.branch'].search([]).ids,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
                }])
        if values:
            user='Password Changed'
            set_password = self.env['change.password.user'].create({
                    "wizard_id": self.env['change.password.wizard'].create({}).id,
                    "user_id": contact.user_ids.id,
                    "user_login": values['username'] or contact.user_ids.login,
                    "new_passwd": values['password']
                })
            set_password.change_password_button()
        return user

    def _merge_names(self,values,update_contact=False):
        #Initialize Variables
        full_name = ''
        old_full_name = {}

        #to recycle the def with update
        if update_contact:
            old_full_name["first_name"] = update_contact.first_name
            old_full_name["last_name"] = update_contact.last_name
            old_full_name["name_ext"] = update_contact.name_ext

        #Merge New Name and Old Name
        for name in ["first_name","last_name","name_ext"]:
            if name in values:
                full_name += ' ' + values[name]
            elif update_contact and old_full_name[name]:
                full_name += ' ' + old_full_name[name]
        
        #Delete the space before the full name
        full_name = full_name[1:]

        return full_name

    def _trim_image(self,values):
        #Initialize Variables
        image_1920 = ""

        #Remove the prepend and retain only Base64 Value
        if "image_1920" in values:
            if values["image_1920"]:
                image_1920 = values["image_1920"][18:]
        return image_1920

    def _contact_fields(self):
        cbiz_fields = [
            "name","shipper_id","type","first_name","last_name","name_ext","phone","mobile","vat","email","image_1920","branch_id"
            ]
        return cbiz_fields

    def _return_contact_values(self,id):
        res_partner = self.env["res.partner"].browse(id)
        return {
            "id": res_partner.id,
            "name": res_partner.name,
            "type": res_partner.type,
            "image_1920": self._http_image(id) or False,
            "shipper_id": res_partner.shipper_id,
            "first_name": res_partner.first_name,
            "last_name": res_partner.last_name,
            "name_ext": res_partner.name_ext,
            "phone": res_partner.phone,
            "mobile": res_partner.mobile,
            "vat": res_partner.vat,
            "email": res_partner.email,
            "branch_id": False,
            "username": res_partner.user_ids.login or False
        }

    def _return_contact_list(self,search_ids):
            #stringify the search_id string to be fed on odoo cursor ORM
            ids = ", ".join(repr(id) for id in search_ids)
            #Odoo Cursor ORM for PostgreSQL Query, Joined the res_partner, res_user, and attachment table
            self.env.cr.execute(_("""
                SELECT * FROM (SELECT
                res_partner.id,
                res_partner.name,
                res_partner.type,
                res_partner.shipper_id,
                res_partner.first_name,
                res_partner.last_name,
                res_partner.name_ext,
                res_partner.phone,
                res_partner.mobile,
                res_partner.vat,
                res_partner.email,
                res_partner.branch_id,
                res_users.login
                FROM res_partner
                LEFT JOIN res_users ON (res_partner.id = res_users.partner_id)
                WHERE res_partner.id IN (%s)) table1 LEFT JOIN
                (SELECT
                ir_attachment.res_id,
                ir_attachment.store_fname
                FROM ir_attachment
                WHERE ir_attachment.res_field='image_1920') table2 ON
                table1.id = table2.res_id
            """,ids))
            #data fetched from postgreSQL temporary cache
            data = self.env.cr.fetchall()
            rows=[]
            #Fast internal looping for the list of users,contacts
            for i in data:
                image = ''
                #verify if there is store_fname value to get it from the filestore attachment
                if i[14]:
                    imagedata = ''
                    imagery = self.env['ir.attachment']._file_read(i[14])
                    imagedata = base64.b64encode(imagery or b'')
                    image = "data:image;base64," + imagedata.decode('utf-8')
                datarow={
                    "id":i[0] or False,
                    "name":i[1] or False,
                    "type":i[2] or False,
                    "shipper_id":i[3] or False,
                    "first_name":i[4] or False,
                    "last_name":i[5] or False,
                    "name_ext":i[6] or False,
                    "phone":i[7] or False,
                    "mobile":i[8] or False,
                    "vat":i[9] or False, 
                    "email":i[10] or False,
                    "branch_id":i[11] or False,
                    "username":i[12] or False,
                    "image_1920": image or False
                }
                rows.append(datarow)
            return rows

    def _http_image(self,id):
        status,headers,data = self.env["ir.http"].binary_content(
            model="res.partner", id=id, field="image_1920"
        )
        if data:
            return "data:image;base64," + data.decode('utf-8')
        else:
            return False