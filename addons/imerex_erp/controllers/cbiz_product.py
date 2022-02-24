
from odoo import fields, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component

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
            error_return = {"error": "No Product with given ID"}
            return error_return
        final_search = self.env['product.template'].search([("id","=",search_ids)])
        return_value = {}
        for id in final_search.ids:
            return_value.update(self._return_journal_values(id))
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
            search_ids = self.env['product.template'].search([("name","like",name)]).ids
        if code:
            search_code = self.env['product.template'].search([("code","=",code)]).ids
            search_ids = list(set(search_code)&set(search_ids))
        if not search_ids:
            error_return = {"error":"No Product with given name"}
            return error_return
        final_search = self.env['product.template'].search([("id","=",search_ids)])
        return_value = []
        for id in final_search.ids:
            return_value.append(self._return_journal_values(id))
        if len(final_search.ids) > 1:
            return {"products": return_value}
        else:
            return {
                "id": final_search.id,
                "code": final_search.code,
                "name": final_search.display_name
            }

    def _validator_return_get(self):
        return {
            "id":{"type": "integer"},
            "name":{"type": "string"},
            "error": {}
        }

    def _validator_search(self):
        return {
            "code":{"type": "string", "required": False},
            "name":{"type": "string", "required": False},            
        }

    def _validator_return_search(self):
        schema = {
            "id": {"type": "integer"},
            "code":{"type": "string"},
            "name":{"type": "string"},
        }
        return {
            "products": {
                "type": "list",
                "schema": {"type": "dict", "schema": schema},
                },
            "id": {"type": "integer"},
            "code":{"type": "string"},
            "name":{"type": "string"},
            "error": {}
        }
        
    def _return_journal_values(self,id):
        product = self.env['product.template'].browse(id)
        return {
            "id": product.id,
            "code": product.code if product.code else '',
            "name": product.display_name,
        }

    @restapi.method(
        [(['/code/'], "GET")],
        input_param=restapi.CerberusValidator("_validator_code"),
        output_param=restapi.CerberusValidator("_validator_return_code")
        )
    def code(self,code=''):
        """
        Search Product by Code
        """
        search_ids = self.env['product.template'].search([("code","=",code)])
        return {
            "id": search_ids.id,
            "code": search_ids.code,
            "name": search_ids.name
            }

    def _validator_code(self):
        return {
            "code": {"type": "string", "required": False, "nullable": True}
        }

    def _validator_return_code(self):
        return {
            "id":{"type": "integer"},
            "code":{"type": "string"},
            "name":{"type": "string"},
            "error": {}
        }

