
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

    @http.route(['/invoicedownload/<string:reference>'], type='http', auth="public", website=True)
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