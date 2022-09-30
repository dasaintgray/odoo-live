from datetime import datetime
import PyPDF2
from io import BytesIO
import json
import pytz
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from odoo import fields, _
from odoo.exceptions import ValidationError
from odoo.http import request, content_disposition
from odoo import http, _
from odoo.tests.common import Form
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
    def search(self, **kwargs):
        """
        Search Invoice by Reference and return ID and Name
        """
        ref = kwargs['ref']
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
            "name": {}
        }

    @restapi.method(
        [(['/note/','POST'])],
        input_param=restapi.CerberusValidator("_validator_electronic_notes_create"),
    )
    def electronic_notes(self, **kwargs):
        hawb = kwargs['hawb']
        invoice = self.env['account.move'].search([("ref","=",hawb)])

        payment_fields = ['payment_type','payment_date','payment_amount']
        payment_fields_verification = []

        error_string = ""
        for key in payment_fields:
            if key not in kwargs:
                payment_fields_verification.append(key)
            else:
                if not kwargs[key]:
                    payment_fields_verification.append(key)
        
        if payment_fields_verification and payment_fields != payment_fields_verification:
            for field in payment_fields_verification:
                error_string += field + ", "

            error_string = error_string[:-2]
            raise ValidationError(_("%s - required",error_string))

        if 'company_id' not in kwargs:
            kwargs['company_id'] = 1

        if 'payment_type' in kwargs:
            payment_journal_id = self.env['cbiz.api.cargoapi'].cargo_payment_method(kwargs['payment_type'])[0]


        note_date = self._time_store(kwargs['note_date'])
        note_journal_id = self.env['account.journal'].search([('name','=','Electronic Notes')]).id
        note_product_id = self.env['product.product'].search([("name","=","Electronic Note Change")])

        if kwargs['type'] == 'debit':
            note = self.env['account.move'].create({
                "debit_origin_id": invoice.id,
                "move_type": "out_invoice",
                "partner_id": invoice.partner_id.id,
                "ref": invoice.ref + " Debit Note: " + str(invoice.debit_note_count + 1) + " - " + kwargs['reason'],
                "invoice_date": note_date,
                "branch_id": invoice.branch_id.id,
                "invoice_date_due": note_date,
                "journal_id": note_journal_id
            })
        else:
            invoices = self.env['account.move'].search([("ref","like",hawb),('move_type','in',['out_refund','out_invoice'])])
            invoices_data = self.env['cbiz.api.cargoapi'].balance_check(invoices)
            if invoices_data['total_balance'] <= 0:
                raise ValidationError("You cannot create a credit note with" + hawb + " balance zero and below")
            refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.id).create({
                'reason': kwargs['hawb'] + " Credit Note: " + str(len(self.env['account.move'].search([('ref','like',kwargs['hawb']),('move_type','=',"out_refund")]).ids) + 1) + " - " + kwargs['reason'],
                'refund_method': 'refund',
                'date_mode': 'custom',
                'date': note_date,
                'journal_id': note_journal_id
            })
            refund_wizard.reverse_moves()
            note = refund_wizard.new_move_ids
            note.write({
                'invoice_date': note_date,
                'invoice_line_ids': False
            })

        note_form = Form(note)

        with note_form.invoice_line_ids.new() as line_form:
            line_form.product_id = note_product_id
            line_form.account_id = note_product_id.property_account_income_id
            line_form.name = kwargs['hawb'] + " " + note_product_id.name + " " + kwargs['reason']
            line_form.price_unit = kwargs['note_amount']

        note = note_form.save()
        note.action_post()

        pending_payments = json.loads(note.invoice_outstanding_credits_debits_widget)
        if pending_payments:
            if pending_payments['content']:
                for i in pending_payments['content']:
                    if kwargs['hawb'] in i['journal_name']:
                        note.js_assign_outstanding_line(i['id'])

        if not payment_fields_verification and kwargs['type'] == 'debit':
            payment = note.env['account.payment.register'].with_context({
                "active_model": "account.move",
                "active_ids": note.id
            }).create([{
                "payment_date": kwargs["payment_date"],
                "amount": kwargs["payment_amount"],
                "journal_id": payment_journal_id,
                "payment_method_id": 1,
                "company_id": kwargs["company_id"]
            }])
            payment.action_create_payments()
        return {
            "id": note.id,
            "name": note.name,
            "total": note.amount_total_signed,
            "date_created": fields.Datetime.to_string(note.invoice_date),
            "total_balance": note.amount_residual_signed,
            "ref": note.ref
        }


    @restapi.method(
        [(['/note/<string:hawb>','GET'])],
        # input_param=restapi.CerberusValidator("_validator_electronic_notes_create"),
    )
    def electronic_notes_summary(self, hawb):
        invoices = request.env['account.move'].sudo().search([('ref','=',hawb),('state','=','posted'),('move_type','in',['out_refund','out_invoice'])])
        invoices += request.env['account.move'].sudo().search([('ref','like',hawb + " "),('state','=','posted'),('move_type','in',['out_refund','out_invoice'])])
        if not invoices:
            return None

        domain = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # domain = domain.replace("http","https")
        download = domain  + "/iddl/"

        invoices_data = {
            "invoices": [],
            "debitnotes": [],
            "creditnotes": [],
            "totalnotes": 0,
            "total": 0,
            "total_balance": 0,
            "summary_download": domain + "/idc/" + hawb + ".pdf"
        }

        for invoice in invoices:

            if invoice.move_type == "out_refund":
                key = "creditnotes"
            elif invoice.move_type == "out_invoice" and invoice.ref == hawb:
                key = "invoices"
            else:
                key = "debitnotes"
            
            invoices_data[key].append({
                "id": invoice.id,
                "name": invoice.name,
                "total": invoice.amount_total_signed,
                "balance": invoice.amount_residual_signed,
                "date_created": invoice.invoice_date,
                "ref": invoice.ref,
                "download_link": download + str(invoice.id)
            })
            invoices_data["totalnotes"] += 1 if key != "invoices" else 0
            invoices_data["total"] += invoice.amount_total_signed
            invoices_data["total_balance"] += invoice.amount_residual_signed
        
        return invoices_data

    def _validator_electronic_notes_create(self):
        date_format = lambda s: datetime.strptime(s, '%Y-%m-%d %H:%M:%S') if s else None
        return {
            "type": {
                "type": "string",
                "required": True,
                "allowed": ["debit", "credit"]
                },
            "hawb": {
                "type": "string",
                "required": True
                },
            "note_date": { 
                "type": "datetime",
                "coerce": date_format,
                "required": True
                },
            "note_amount": {
                "type": "float",
                "required": True
            },
            "reason": {
                "type": "string",
                "required": True
                },
            "payment_date": {
                "type": "datetime",
                "empty": True,
                "required": False,
                "nullable": True,
                "coerce": date_format
                },
            "payment_amount": {
                "type": "float",
                "empty": True,
                "required": False,
                "nullable": True,
                },
            "payment_type": {
                "empty": True,
                "required": False,
                "nullable": True,
                "allowed": ["cash", "bank", "stcpay"]
                }
        }

    def _time_store(self, input_date):
        #convert from local to utc as Odoo framework stores date in UTC for easy conversion
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        #convert string to datetime format for local time
        date_order = user_tz.localize(input_date)
        #change timezone to UTC
        date_order_utc = date_order.astimezone(pytz.timezone('UTC'))
        #bring the converted value back to the dict with key date_order
        return fields.Datetime.to_string(date_order_utc)

class PublicInvoice(http.Controller):
    _description="""Public Invoice Download"""

    @http.route(['/publicnote/<string:hawb>'], type='http', auth="public", website=True)
    def electronic_notes_summary(self, hawb):

        invoice = invoices = request.env['account.move'].sudo().search([('ref','=',hawb),('state','=','posted'),('move_type','in',['out_refund','out_invoice'])])
        invoices += request.env['account.move'].sudo().search([('ref','like',hawb + " "),('state','=','posted'),('move_type','in',['out_refund','out_invoice'])])
        if not invoices:
            raise ValidationError("No Invoices for given HAWB")
        domain = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # domain = domain.replace("http","https")
        download = domain  + "/iddl/"
        invoices_data = {
            "invoices": [],
            "debitnotes": [],
            "creditnotes": [],
            "total": 0,
            "total_balance": 0,
            "summary_download": domain + "/idc/" + hawb + '.pdf'
        }

        for invoice in invoices:

            if invoice.move_type == "out_refund":
                key = "creditnotes"
            elif invoice.move_type == "out_invoice" and invoice.ref == hawb:
                key = "invoices"
            else:
                key = "debitnotes"
            invoices_data[key].append({
                "name": invoice.name,
                "total": invoice.amount_total_signed,
                # "balance": invoice.amount_residual_signed,
                "date_created": fields.Datetime.to_string(invoice.invoice_date),
                "ref": invoice.ref,
                "download_link": download + str(invoice.id)
            })
            invoices_data["total"] += invoice.amount_total_signed
            invoices_data["total_balance"] += invoice.amount_residual_signed

        return json.dumps(invoices_data)

    @http.route(['/idl/<string:reference>'], type='http', auth="public", website=True)
    def download_pdf(self, reference):
        invoice = request.env['sale.order'].sudo().search([('name', '=', reference)], limit=1).invoice_ids
        if not invoice:
            return None
        pdf, _ = request.env['ir.actions.report']._get_report_from_name(
            'account.report_invoice_with_payments').sudo()._render_qweb_pdf(
            [int(invoice.id)])
        pdf_http_headers = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
                            ('Content-Disposition', content_disposition('%s - Invoice.pdf' % (invoice.ref)))]
        return request.make_response(pdf, headers=pdf_http_headers)

    @http.route(['/iddl/<int:seq>'], type='http', auth="public", website=True)
    def invoice_download_pdf(self, seq):
        invoice = request.env['account.move'].sudo().browse(seq)
        if not invoice:
            return None
        pdf, _ = request.env['ir.actions.report']._get_report_from_name(
            'account.report_invoice_with_payments').sudo()._render_qweb_pdf(
            [seq])
        pdf_http_headers = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
                            ('Content-Disposition', content_disposition('%s - Invoice.pdf' % (invoice.ref)))]
        return request.make_response(pdf, headers=pdf_http_headers)

    @http.route(['/idc/<string:hawb>','/idc/<string:hawb>.pdf'], type='http', auth="public", website=True)
    def invoice_concatenate_download_pdf(self, hawb, **kwargs):
        invoice  = invoices = request.env['account.move'].sudo().search([('ref', '=', hawb),('state','=','posted'),('move_type','in',['out_refund','out_invoice'])])
        invoices += request.env['account.move'].sudo().search([('ref','like',hawb + " "),('state','=','posted'),('move_type','in',['out_refund','out_invoice'])])
        invoice_ids = invoices.ids
        if not invoice:
            return None
        pdf_list = []
        for id in invoice_ids:
            pdf, _ = request.env['ir.actions.report']._get_report_from_name(
                'account.report_invoice_with_payments').sudo()._render_qweb_pdf(id)
            pdf_list.append(PyPDF2.PdfFileReader(BytesIO(pdf)))
        
        pdfwriter = PyPDF2.PdfFileWriter()

        for pdf_doc in pdf_list:
            for page_number in range(pdf_doc.numPages):
                pageObj = pdf_doc.getPage(page_number)
                pdfwriter.addPage(pageObj)
        
        with BytesIO() as bytes_stream:
            pdfwriter.write(bytes_stream)
            concatenated_pdf = bytes_stream.getvalue()

        pdf_http_headers = [('Content-Type', 'application/pdf'), ('Content-Length', len(concatenated_pdf)),
                            ('Content-Disposition', content_disposition('%s - Invoice.pdf' % (invoice.ref)))]
        return request.make_response(concatenated_pdf, headers=pdf_http_headers)