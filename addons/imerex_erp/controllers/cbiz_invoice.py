
from http.client import OK
from odoo import _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from odoo.exceptions import ValidationError
from odoo.http import request, content_disposition
from odoo import http, _
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
            raise ValidationError("No Invoice with the said reference")
        return_value = {
            "id": res.id,
            "name": res.name
        }
        return return_value

    @restapi.method(
        [(['/creditnote/'], "POST")],
        # input_param=restapi.CerberusValidator("_validator_creditnote"),
        # output_param=restapi.CerberusValidator("_validator_creditnote_search")
        )
    def creditnote(self, params):
        #Check required keys
        for key in ['shipper_id','name','invoice_line_ids','cargo_branch_id']:
            if key not in params:
                raise ValidationError(_("'%s' required!"),key)

        #Search for invoice with given HAWB in ref"
        invoice = self.env['account.move'].search([('ref','=',params['name'])])
        if not invoice:
            raise ValidationError("You cannot create a credit note for a non-existing Invoice")

        #Search for customer with given shipper_id
        customer = self.env['res.partner'].search([('shipper_id','=',str(params['shipper_id']))])
        if not customer:
            raise ValidationError("No customer with the said 'shipper_id'")

        #Search for branch_id with given cargo_branch_id
        branch_id = self.env['res.branch'].search([('cargo_branch_id','=',params['cargo_branch_id'])]).id
        if not branch_id:
            raise ValidationError('No Branch with the given Cargo ID')

        #Credit Note standard values initialization
        values = {
            "ref": "Reversal of: " + invoice.name + " - " + params["name"],
            "move_type": "out_refund",
            "partner_id": customer.id,
            "invoice_date": params["invoice_date"],
            "branch_id": branch_id
        }

        #Completing naming convention "Reversal of: invoice_name - hawb: reason"
        if params["reason"]:
            values["ref"] += ": " + params["reason"]
        else:
            values["ref"] += ": Due to revision in CircuitTrack Transaction"

        #data processing done. pending works are _validators and credit note posting
        return_value = [OK]
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

class PublicInvoice(http.Controller):
    _description="""Public Invoice Download"""

    @http.route(['/idl/<string:reference>'], type='http', auth="public", website=True)
    def download_pdf(self, reference):
        invoice = request.env['account.move'].sudo().search([('ref', '=', reference)], limit=1)
        if not invoice:
            return None
        pdf, _ = request.env['ir.actions.report']._get_report_from_name(
            'account.report_invoice_with_payments').sudo()._render_qweb_pdf(
            [int(invoice.id)])
        pdf_http_headers = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
                            ('Content-Disposition', content_disposition('%s - Invoice.pdf' % (invoice.ref)))]
        return request.make_response(pdf, headers=pdf_http_headers)