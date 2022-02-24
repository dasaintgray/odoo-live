
from odoo import fields, _
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
        res_partner = self.env["res.partner"].search([("id","=",_id)])
        image = self._http_image(_id)
        values = self._return_contact_values(res_partner,image)
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
        output_param=restapi.CerberusValidator("_validator_return_search")
        )
    def search(self, name=False, shipper_id=False, type=False):
        """
        Search Contacts by ID, Name, or Shipper_id
        """
        search_id =  self.env["res.partner"].search([]).ids
        if name:
            name_search = self.env["res.partner"].search([("name","like",name)]).ids
            search_id = name_search
        if shipper_id:
            shipper_id_search = self.env["res.partner"].search([("shipper_id","=",shipper_id)]).ids
            search_id = list(set(search_id)&set(shipper_id_search))
        if type:
            if not type == "all":
                type_search = self.env["res.partner"].search([("type","=",type)]).ids
                search_id = list(set(search_id)&set(type_search))
        partners = self.env["res.partner"].search([("id","=",search_id)])
        if partners:
            partners = partners.browse([i for i in partners.ids])
        rows = []
        res = {"count": len(partners) if partners else 0, "rows": rows}
        if partners:
            for partner in partners:
                rows.append(self._return_contact_values(partner))
        return res

    @restapi.method(
        [(['/<int:_id>'], "PATCH")],
        input_param=restapi.CerberusValidator("_validator_update"),
        output_param=restapi.CerberusValidator("_validator_return_update")
        )
    def update(self, _id, **params):
        """
        Update Contact information
        """
        partner = self._update_contact(_id,params)
        return partner

    def _validator_return_get(self):
        res = self._validator_contact_fields()
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

    def _validator_return_search(self):
        schema = self._validator_return_get()
        schema.pop("image_1920")
        return {
            "count": {"type": "integer", "required": True},
            "rows": {
                "type": "list",
                "required": True,
                "schema": {"type": "dict", "schema": schema},
            },
        }

    def _validator_update(self):
        res = self._validator_contact_fields()
        res.pop("id")
        res.pop("name")
        return res

    def _validator_return_update(self):
        res = {
            "update": {}
        }
        return res

    def _create_contact(self,values):
        contact_info = {}
        create_contact = self.env["res.partner"]
        values["image_1920"] = self._trim_image(values)
        values["name"] = self._merge_names(values)
        contact_fields = self._contact_fields()
        for field in contact_fields:
            if field in values:
                if field == "branch_id":
                    contact_info.update({
                    field : False
                })
                else:
                    contact_info.update({
                        field : values[field]
                    })
        created_contact = create_contact.create(contact_info)
        return_contact = self._return_contact_values(created_contact,values["image_1920"])
        return return_contact

    def _update_contact(self,id,values):
        contact_info = {}
        update_contact = self.env["res.partner"].browse(id)
        values["image_1920"] = self._trim_image(values)
        values["name"] = self._merge_names(values,update_contact)
        contact_fields = self._contact_fields()
        for field in contact_fields:
            if field in values:
                if field == "branch_id":
                    contact_info.update({
                    field : False
                })
                else:
                    contact_info.update({
                        field : values[field]
                    })
        if not contact_info["image_1920"]:
            contact_info.pop("image_1920")
        updated_contact = update_contact.write(contact_info)
        return {"update": updated_contact}

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
        }
        return res

    def _merge_names(self,values,update_contact=False):
        full_name = ''
        old_full_name = {}
        if update_contact:
            old_full_name["first_name"] = update_contact.first_name
            old_full_name["last_name"] = update_contact.last_name
            old_full_name["name_ext"] = update_contact.name_ext
        for name in ["first_name","last_name","name_ext"]:
            if name in values:
                full_name += ' ' + values[name]
            elif update_contact:
                full_name += ' ' + old_full_name[name]
        full_name = full_name[1:]
        return full_name

    def _trim_image(self,values):
        image_1920 = ""
        if "image_1920" in values:
            if values["image_1920"]:
                image_1920 = values["image_1920"][18:]
        return image_1920

    def _contact_fields(self):
        cbiz_fields = [
            "name","shipper_id","type","first_name","last_name","name_ext","phone","mobile","vat","email","image_1920","branch_id"
            ]
        return cbiz_fields

    def _return_contact_values(self,create_contact,image_1920=False):
        return_contact = {
            "id": create_contact.id,
            "name": create_contact.name,
            "type": create_contact.type,
            "image_1920": image_1920,
            "shipper_id": create_contact.shipper_id,
            "first_name": create_contact.first_name,
            "last_name": create_contact.last_name,
            "name_ext": create_contact.name_ext,
            "phone": create_contact.phone,
            "mobile": create_contact.mobile,
            "vat": create_contact.vat,
            "email": create_contact.email,
            "branch_id": False
        }
        if not return_contact['image_1920']:
            return_contact['image_1920'] = self._http_image(create_contact.id)
        return return_contact

    def _http_image(self,id):
        status,headers,image = self.env["ir.http"].binary_content(
            model="res.partner", id=id, field="image_1920"
        )
        if isinstance(image,bytes):
            image_string = "data:image;base64," + image.decode('utf-8')
        else:
            image_string = "data:image;base64," + image
        return image_string
