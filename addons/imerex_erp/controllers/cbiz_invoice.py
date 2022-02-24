
from odoo import _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component

class cBizInvoiceService(Component):
    _inherit = "base.rest.service"
    _name = "cbiz.invoice.service"
    _usage = "invoice"
    _collection = "cbiz.services.api"
    _description = """
        Invoice API Service

        Service used to search invoice references
    """

    @restapi.method(
        [(['/'], "GET")],
        input_param=restapi.CerberusValidator("_validator_search"),
        output_param=restapi.CerberusValidator("_validator_return_search")
        )
    def search(self, ref):
        """
        Search Invoice by Reference and return ID and Name
        """
        res = self.env['account.move'].search([("ref","=",ref)])
        if not res:
            error = {"error":"No Invoice with the said reference"}
            return error
        return_value = {
            "id": res.id,
            "name": res.name
        }
        return return_value

    def _validator_search(self):
        return {
            "ref": {"type": "string"},
            }

    def _validator_return_search(self):
        return {
            "id": {"type": "integer"},
            "name": {},
            "error": {}
        }