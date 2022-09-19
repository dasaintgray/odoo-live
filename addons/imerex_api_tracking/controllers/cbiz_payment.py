from odoo import fields, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from odoo.exceptions import ValidationError
import json

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
        # output_param=restapi.CerberusValidator("_validator_return_create")
        )
    def create(self, **params):
        """
        Create Payment
        """
        create_payment = self._create_payment(params)
        return create_payment

    def _create_payment(self, values):
        sale_order = self.env['sale.order'].search([('name','=',values['name'])])
        payment_return = []
        if not sale_order.invoice_ids:
            raise ValidationError("You cannot create a payment for a non-existing Invoice")
        for invoice in sale_order.invoice_ids:
            if invoice.state != 'posted':
                raise ValidationError("One of the invoices are not posted!")
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
            payment_return.append(self._return_response_payment(payment))
        return payment_return
    
    @restapi.method(
        [(['/void'], "POST")],
        input_param=restapi.CerberusValidator("_validator_void"),
        # output_param=restapi.CerberusValidator("_validator_return_create")
        )
    def void(self,**params):
        """
        name: KSAXXXXX
        payment_sequence: X
        """
        invoices = self.env['sale.order'].search([('name','=', params['name'])]).invoice_ids
        payment_ids = ['NULL']
        for invoice in invoices:
            payments = json.loads(invoice.invoice_payments_widget)
            for payment in payments['content']:
                payment_ids.append(payment['account_payment_id'])
        if len(payment_ids) > 1:
            void = self.env['account.payment'].search([('id','=',payment_ids[params['payment_sequence']])])
            void.action_draft()
            void.action_cancel()
            if void.state == 'cancel':
                return {"void": True}
        else:
            raise ValidationError("You cannot void this payment or no payment available!")

    def _validator_void(self):
        res = {
            "name":{},
            "payment_sequence":{"type": "integer"}
        }
        return res

    def _validator_create(self):
        res = {
            "payment_date":{},
            "name":{},
            "company_id":{"type": "integer"},
            "payment_journal_id":{"type": "float"},
            "amount":{"type": "float"}
        }
        return res

    def _return_response_payment(self,payment):
        sale_order = self.env['account.move'].search([('name','=',payment.communication)]).ref
        res = {
            "name": sale_order,
            "invoice_name": payment.communication,
            "amount": payment.amount
        }
        return res

    @restapi.method(
        [(['/hawb/'], "POST")],
        input_param=restapi.CerberusValidator("_validator_create_v2"),
        )
    def cargo_v2_payments(self, **kwargs):
        if "company_id" not in kwargs:
            kwargs["company_id"] = 1
        create_payment = self._create_payment_v2(kwargs)
        return create_payment

    def _create_payment_v2(self, values):
        hawb = values['name']
        payment_type = values['payment_type']
        payment_date = values['payment_date']
        payment_amount = values['amount']
        payment_amount_balance = values['amount']
        company_id = values['company_id']
        invoices = self.env['account.move'].search([('ref','like',hawb),('state','=','posted'),('move_type','in',['out_refund','out_invoice'])])
        payment_journal_id = self.env['cbiz.api.cargoapi'].cargo_payment_method(payment_type)[0]
        payment_return = []

        if not invoices:
            raise ValidationError("You cannot create a payment for a non-existing Invoice")

        invoices_data = self.env['cbiz.api.cargoapi'].balance_check(invoices)

        if (invoices_data['total_balance'] > 0 and payment_amount < 0) or (invoices_data['total_balance'] < 0 and payment_amount > 0):
            raise ValidationError("Wrong payment amount, balance is: " + str(invoices_data['total_balance']))
        else:
            if abs(invoices_data['total_balance']) == 0:
                raise ValidationError(hawb + ": No Balance")
            if (abs(invoices_data['total_balance']) - abs(payment_amount)) < 0:
                raise ValidationError(hawb + ": Overpayment")


        for invoice in invoices_data['invoices']:
            if abs(payment_amount_balance) > abs(invoice['balance']):
                payment = invoice['balance']
            else:
                payment = payment_amount_balance
            
            if invoice['balance'] != 0 and payment_amount_balance > 0:
                payment_amount_balance -= payment
                payment = invoice['object'].env['account.payment.register'].with_context({
                                "active_model":"account.move",
                                "active_ids": invoice['id']
                            }).create([{
                                "payment_date": payment_date,
                                "amount": abs(payment),
                                "journal_id": payment_journal_id,
                                "payment_method_id": 1,
                                "company_id": company_id
                            }])
                payment.action_create_payments()
                payment_return.append(self._return_response_payment_v2(payment,invoice))
        return payment_return

    def _validator_create_v2(self):
        res = {
            "payment_date":{"required": True},
            "name":{"required": True},
            "payment_type":{"type": "string", "required": True, "allowed": ["cash","bank","stcpay"]},
            "amount":{"type": "float", "required": True},
            "company_id": {"type":"integer", "empty": True}
        }
        return res

    def _return_response_payment_v2(self,payment,invoice):
        res = {
            "name": invoice['name'],
            "reference": invoice['ref'],
            "balance": invoice['object'].amount_residual,
            "amount": payment.amount
        }
        return res