
from xml.dom import ValidationErr
from odoo import fields, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component

from odoo.exceptions import ValidationError
class cBizProductService(Component):
    _inherit = "base.rest.service"
    _name = "cbiz.product.service"
    _usage = "product"
    _collection = "cbiz.services.api"
    _description = """
        Product API Service

        Service used to search Products
    """

    @restapi.method(
        [(['/<int:id>'], "GET")],
        output_param=restapi.CerberusValidator("_validator_return_get")
        )
    def get(self, id):
        """
        Search Product by ID
        """
        search_ids = self.env['product.template'].search([("id","=",id)]).ids
        if not search_ids:
            raise ValidationError("No Product Found")
        final_search = self.env['product.template'].search([("id","=",search_ids)])
        return_value = {}
        for id in final_search.ids:
            return_value.update(self._return_product_values(id))
        return return_value

    @restapi.method(
        [(['/search'], "GET")],
        input_param=restapi.CerberusValidator("_validator_search"),
        output_param=restapi.CerberusValidator("_validator_return_search")
        )
    def search(self,name='',code=''):
        """
        Search Product by Name
        """
        search_ids = self.env['product.template'].search([]).ids
        if name:
            search_ids = self.env['product.template'].search([("|"),("name","like",name),("default_code","=",name)]).ids
        if code:
            search_code = self.env['product.template'].search([("code","=",code)]).ids
            search_ids = list(set(search_code)&set(search_ids))
        if not search_ids:
            raise ValidationError("No Product Found")
        final_search = self.env['product.template'].search([("id","=",search_ids)])
        return_value = []
        for id in final_search.ids:
            return_value.append(self._return_product_values(id))
        return {"products": return_value}

    @restapi.method(
        [(['/code/'], "GET")],
        input_param=restapi.CerberusValidator("_validator_code"),
        output_param=restapi.CerberusValidator("_validator_return_code")
        )
    def code(self,code=''):
        """
        Search Product by Code
        """
        search_id = self.env['product.template'].search([("code","=",code)]).id
        product = self._return_product_values(search_id)
        return product

    def _validator_code(self):
        return {
            "code": {"type": "string", "required": False, "nullable": True}
        }

    def _validator_return_code(self):
        return_code = self._validator_return_get()
        return return_code

    def _validator_return_get(self):
        return {
            "id": {"type": "integer"},
            "code":{"type": "string"},
            "name":{"type": "string"},
            "description": {"type":"string"},
            "image": {"type":"string"}
        }

    def _validator_search(self):
        return {
            "code":{"type": "string", "required": False},
            "name":{"type": "string", "required": False},            
        }

    def _validator_return_search(self):
        schema = self._validator_return_get()
        return_search = self._validator_return_get()
        return_search.update({
            "products": {
                "type": "list",
                "schema": {"type": "dict", "schema": schema}
            }
        })
        return return_search
        
    def _return_product_values(self,id):
        product = self.env['product.template'].browse(id)
        image = self._http_image(id)
        return {
            "id": product.id,
            "code": product.code or '',
            "name": product.display_name,
            "description": product.description_sale or '',
            "image": image
        }

    def _http_image(self,id):
        status,headers,image = self.env["ir.http"].binary_content(
            model="product.template", id=id, field="image_1920"
        )
        if isinstance(image,bytes):
            image_string = "data:image;base64," + image.decode('utf-8')
        else:
            image_string = "data:image;base64," + image
        if image_string == "data:image;base64,":
            image_string = ''
        return image_string

