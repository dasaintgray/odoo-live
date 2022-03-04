
from odoo import fields, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from odoo.exceptions import ValidationError
class cBizBranchService(Component):
    _inherit = "base.rest.service"
    _name = "cbiz.branch.service"
    _usage = "branch"
    _collection = "cbiz.services.api"
    _description = """
        Branch API Service

        Service used to search branches
    """

    @restapi.method(
        [(['/<int:id>'], "GET")],
        output_param=restapi.CerberusValidator("_validator_return_get")
        )
    def get(self, id):
        """
        Search branch by ID
        """
        search_ids = self.env['res.branch'].search([("id","=",id)]).ids
        if not search_ids:
            raise ValidationError("No Branch with given parameters")
        final_search = self.env["res.branch"].search([("id","=",search_ids)])
        return_value = {}
        for id in final_search.ids:
            return_value.update(self._return_branch_values(id))
        return return_value

    @restapi.method(
        [(['/search'], "GET")],
        input_param=restapi.CerberusValidator("_validator_search"),
        )
    def search(self,name='',company=''):
        """
        Search branch by Name or company name
        """
        search_ids = self.env['res.branch'].search([]).ids
        if name:
            search_name = self.env['res.branch'].search([("name","like",name)]).ids
            search_ids = search_name
        if company:
            search_company = self.env['res.branch'].search([("company_id.name","like",company)]).ids
            search_ids = list(set(search_company)&set(search_ids))
        if not search_ids:
            raise ValidationError("No Branch with given parameters")
        final_search = self.env["res.branch"].search([("id","=",search_ids)])
        return_value = []
        for id in final_search.ids:
            return_value.append(self._return_branch_values(id))
        return return_value
        

    def _validator_return_get(self):
        return {
            "id":{"type": "integer"},
            "name":{"type": "string"},
            "company":{"type":"string"}
        }


    def _validator_search(self):
        return {
            "name":{"type": "string", "required": False},
            "company":{"type": "string", "required": False},
        }

    def _validator_return_search(self):
        schema = {
            "id": {"type": "integer"},
            "name":{"type": "string"},
            "company":{"type":"string"}
        }
        return {
            "branches": {
                "type": "list",
                "schema": {"type": "dict", "schema": schema},
                }
        }
        
    def _return_branch_values(self,id):
        branch = self.env["res.branch"].browse(id)
        return {
            "id": branch.id,
            "name": branch.name,
            "company": branch.company_id.name
        }