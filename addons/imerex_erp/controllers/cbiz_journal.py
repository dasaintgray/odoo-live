
from odoo import  _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component

class cBizJournalService(Component):
    _inherit = "base.rest.service"
    _name = "cbiz.journal.service"
    _usage = "journal"
    _collection = "cbiz.services.api"
    _description = """
        Journal API Service

        Service used to search journals
    """

    @restapi.method(
        [(['/<int:id>'], "GET")],
        )
    def get(self, id):
        """
        Search journal by ID
        """

        search_ids = self.env['account.journal'].search([("id","=",id)]).ids
        if not search_ids:
            error_return = {"error": "No Journal with given parameters"}
            return error_return
        final_search = self.env['account.journal'].search([("id","=",search_ids)])
        
        return_value = {}
        for id in final_search.ids:
            return_value.update(self._return_journal_values(id))

        return return_value

    @restapi.method(
        [(['/search'], "GET")],
        input_param=restapi.CerberusValidator("_validator_search")
        )
    def search(self,name='',company=''):
        """
        Search journal by Name or company name
        """
        search_ids = self.env['account.journal'].search([]).ids
        if name:
            search_name = self.env['account.journal'].search([("name","like",name)]).ids
            search_ids = search_name
        if company:
            search_company = self.env['account.journal'].search([("company_id.name","like",company)]).ids
            search_ids = list(set(search_company)&set(search_ids))
        if not search_ids:
            error_return = {"error":"No Journal with given parameters"}
            return error_return

        final_search = self.env['account.journal'].search([("id","=",search_ids)])

        return_value = []
        for id in final_search.ids:
            return_value.append(self._return_journal_values(id))
            
        return return_value

    def _validator_search(self):
        return {
            "name":{"type": "string", "required": False},
            "company":{"type": "string", "required": False},
        }
        
    def _return_journal_values(self,id):
        journal = self.env['account.journal'].browse(id)
        return {
            "id": journal.id,
            "name": journal.name,
            "company_id": journal.company_id.id,
            "company": journal.company_id.name
        }
