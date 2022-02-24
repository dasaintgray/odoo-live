
from odoo import fields, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component

class cBizPaymentService(Component):
    _inherit = "base.rest.service"
    _name = "cbiz.payment.service"
    _usage = "payment"
    _collection = "cbiz.services.api"
    _description = """
        Payment API Service

        Service used to register payment
    """
    @restapi.method(
        [(['/'], "POST")],
        input_param=restapi.CerberusValidator("_validator_create"),
        output_param=restapi.CerberusValidator("_validator_return_create")
        )
    def create(self, **params):
        """
        Create Payment
        """
        create_payment = self._create_payment(params)
        return create_payment

    def _create_payment(self, values):
        invoice = self.env["account.move"].search([('id','=',values['invoice_id'])])
        if not invoice:
            return {"error": _("No Invoice Found with requested ID: %s",values['invoice_id'])}
        payment = invoice.env['account.payment.register'].with_context({
                        "active_model":"account.move",
                        "active_ids":invoice.id
                    }).create([{
                        "payment_date": values['payment_date'],
                        "amount": values['amount'],
                        "journal_id": values['payment_journal_id'],
                        "payment_method_id": 1,
                        "company_id": values['company_id']
                    }])
        payment.action_create_payments()
        payment_return = self._return_response_payment(payment)
        return payment_return

    def _validator_create(self):
        res = {
            "payment_date":{},
            "invoice_id":{
                "type": "integer",
                "required": True
            },
            "company_id":{"type": "integer"},
            "payment_journal_id":{"type": "integer"},
            "amount":{"type": "integer"}
        }
        return res

    def _validator_return_create(self):
        res = {
            "name": {},
            "amount":{},
            "error": {"nullable": True}
        }
        return res

    def _return_response_payment(self,payment):
        res = {
            "name": payment.communication,
            "amount": payment.amount
        }
        return res