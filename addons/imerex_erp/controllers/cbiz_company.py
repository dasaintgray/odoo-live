
from odoo import fields, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from odoo.exceptions import ValidationError
class cBizCompanyService(Component):
    _inherit = "base.rest.service"
    _name = "cbiz.company.service"
    _usage = "company"
    _collection = "cbiz.services.api"
    _description = """
        Company API Service

        Service used to search companies
    """

    @restapi.method(
        [(['/<int:id>'], "GET")],
        output_param=restapi.CerberusValidator("_validator_return_get")
        )
    def get(self, id):
        """
        Search company by ID
        """
        search_ids = self.env['res.company'].search([("id","=",id)]).ids
        if not search_ids:
            raise ValidationError("No Company with given parameters")
        final_search = self.env["res.company"].search([("id","=",search_ids)])
        return_value = {}
        for id in final_search.ids:
            return_value.update(self._return_company_values(id))
        return return_value

    @restapi.method(
        [(['/search'], "GET")],
        input_param=restapi.CerberusValidator("_validator_search"),
        output_param=restapi.CerberusValidator("_validator_return_search")
        )
    def search(self,name):
        """
        Search company by Name
        """
        search_ids = self.env['res.company'].search([("name","like",name)]).ids
        if not search_ids:
            raise ValidationError("No Company with given parameters")
        final_search = self.env["res.company"].search([("id","=",search_ids)])
        return_value = []
        for id in final_search.ids:
            return_value.append(self._return_company_values(id))
        return {"companies": return_value}
        
    def _validator_return_get(self):
        return {
            "id":{"type": "integer"},
            "name":{"type": "string"},
        }

    def _validator_search(self):
        return {
            "name":{"type": "string", "required": True},
        }

    def _validator_return_search(self):
        schema = {
            "id": {"type": "integer"},
            "name":{"type": "string"},
        }
        return {
            "companies": {
                "type": "list",
                "schema": {"type": "dict", "schema": schema},
                }
        }
        
    def _return_company_values(self,id):
        company = self.env["res.company"].browse(id)
        return {
            "id": company.id,
            "name": company.name
        }

