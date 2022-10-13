
from optparse import Values
import pytz
from datetime import tzinfo
from odoo import fields, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from odoo.exceptions import ValidationError
import json

from odoo.addons.imerex_api_tracking.controllers.cbiz_payment import cBizPaymentService
class cBizSaleOrderService(Component):
    _inherit = "base.rest.service"
    _name = "cbiz.sale.order.service"
    _usage = "sale_order"
    _collection = "cbiz.services.api"
    _description = """
        Sale Order API Service

        Service used to create Sale Order,
        and automatic Product Movement, and Invoice
    """
    @restapi.method(
        [(['/'], "POST")],
        input_param=restapi.CerberusValidator("_validator_create"),
        output_param=restapi.CerberusValidator("_validator_return_create")
        )
    def create(self, **params):
        """
        Create Sales Order
        """
        for key in ['name','order_line']:
            if key not in params:
                raise ValidationError(_("%s is required!",key))
        created_sale_order = self._create_sale_order(params)
        return created_sale_order

    @restapi.method(
        [(['/cargo/'], "POST")],
        input_param=restapi.CerberusValidator("_validator_create_cargo"),
        output_param=restapi.CerberusValidator("_validator_return_create")
        )
    def create_cargo(self, **params):
        """
        Create Sales Order
        """
        for key in ['name','order_line']:
            if key not in params:
                raise ValidationError(_("%s is required!",key))
        created_sale_order = self._create_cargo_sale_order(params)
        return created_sale_order

    def _create_cargo_sale_order(self,values):
        #check shipper_id to sync with CircuitTrack
        if 'shipper_id' in values:
            if 'partner_id' in values:
                raise ValidationError("Do not use both 'shipper_id' and 'partner_id'")
            if values['shipper_id']:
                created_partner = self.env['cbiz.api.cargoapi'].cargo_sync_shipper(values['shipper_id'])
                values['partner_id'] = created_partner.id

        #use cargo_branch_id to search for branch_id which is required by sale order
        if 'cargo_branch_id' in values:
            values['branch_id'] = self.env['res.branch'].search([('cargo_branch_id','=',values['cargo_branch_id'])]).id
            if not values['branch_id']:
                raise ValidationError('No Branch with the given Cargo ID')

        #default value for company_id
        if 'company_id' not in values:
            values['company_id'] = 1

        #Check if company has branches or not
        if 'branch_id' not in values:
            test_branch_in_company = self.env['res.branch'].search([('company_id','=',values['company_id'])]).ids
            if test_branch_in_company:
                raise ValidationError('Branch is required in the given Company!')

        sale_order_fields = self._sale_order_fields()
        sale_order_values={}

        #convert from local TZ to UTC
        values['date_order'] = self._time_store(values['date_order'])

        #serialize order fields except for order_line
        for order_data in sale_order_fields:
            if order_data in values:
                if not order_data == 'order_line':
                    sale_order_values.update({
                            order_data: values[order_data]
                        })

        #create sales order without orderline
        created_sale_order = self.env['sale.order'].create(sale_order_values)

        #create sales order_line and attach to sales order
        sale_order_line_fields = self._sale_order_line_fields()

        #serialize order_line fields
        for order_line_item in values['order_line']:
            order_line_values={}
            order_line_item_name = False
            if 'code' in order_line_item:
                order_line_item['product_id'] = self.env['product.template'].search([('code','=',order_line_item['code'])]).id
            if 'id' in order_line_item:
                order_line_item['product_id'] = self.env['product.template'].browse(int(order_line_item['id'])).id
            if 'product_uom_qty' not in order_line_item:
                order_line_item['product_uom_qty'] = 1
            if 'description' in order_line_item:
                if order_line_item['description']:
                    order_line_item_name = order_line_item.pop('description')
                else:
                    order_line_item.pop('description')
            for order_line_data in sale_order_line_fields:
                if order_line_data in order_line_item:
                    order_line_values.update({
                        order_line_data: order_line_item[order_line_data]
                    })
            order_line_values.update({
                "order_id": created_sale_order.id
            })
            created_sale_order_lines = self.env['sale.order.line'].create(order_line_values)
            if order_line_item_name:
                created_sale_order_lines.update(
                    {"name": order_line_item_name}
                )
        #confirm the sales_order
        created_sale_order.action_confirm()

        #confirm invoice since we are not adding payment_journal_id
        for invoice in created_sale_order.invoice_ids:
            invoice.action_post()

        create_payment = cBizPaymentService._create_batch_payment_v2(self,{
            "name": values['name'],
            "company_id": values["company_id"],
            "payment_date": values["date_order"],
            "payment": values['payments']
            })
        #get return value to dict instead of model
        return_sale_order = self._return_create_values(created_sale_order)
        return_sale_order.update({'payment':create_payment})
        return return_sale_order

    def _return_response_payment_v2(self,payment,invoice):
        res = {
            "name": invoice['name'],
            "reference": invoice['ref'],
            "balance": invoice['object'].amount_residual,
            "amount": payment.amount
        }
        return res

    def _validator_create_cargo(self):
        item_schema = {
            "code": {"type": "string"},
            "id": {},
            "product_uom_qty": {"type": "float"},
            "price_unit": {"type": "float"},
            "description": {
                "type": "string",
                "empty": True,
                "nullable": True
            }
        }
        payment_item_schema = {
            "payment_type":{"type": "string", "required": True, "allowed": ["cash","bank","stcpay"]},
            "amount":{"type": "float", "required": True}
            }
        schema = {
            "name":{
                "type": "string",
                "required": True
            },
            "shipper_id":{},
            "date_order":{},
            "partner_id":{"type": "integer"},
            "company_id": {"type": "integer"},
            "cargo_branch_id":{"type": "integer"},
            "payments":{
                    "type": "list",
                    "required": False,
                    "empty": True,
                    "nullable": True,
                    "schema": {"type": "dict", "schema": payment_item_schema},
                    },
            "client_order_ref": {"type": "string"},
            "order_line": {
                "type": "list",
                "schema": {"type": "dict", "schema": item_schema},
            },
        }
        return schema


    # @restapi.method(
    #     [(['/amendments/'], "POST")],
    #     input_param=restapi.CerberusValidator("_validator_amendments"),
    #     output_param=restapi.CerberusValidator("_validator_return_amendments")
    #     )
    def amendments(self, **params):
        #Check for required Keys
        for key in ['name','date_order']:
            if key not in params:
                raise ValidationError(_("%s is required!",key))
        
        #Search for invoice with given HAWB in ref"
        sale_order = self.env['sale.order'].search([('name','=',params['name'])])

        #Check invoice within Sales Order
        if not sale_order:
            raise ValidationError("No Sale Order with given name")
        elif sale_order.state != 'sale':
            raise ValidationError("This item is not posted")
        elif not sale_order.invoice_ids:
            raise ValidationError("You cannot create a credit note for a non-existing Invoice")

        #Convert Local Time to UTC Time for Postgresql Saving
        date_order = self._time_store(params['date_order'])

        #initialize variables
        log_note = "Cancelled by CircuitTrack due to Transaction Edit"
        existing_payment_amount = 0
        existing_invoices = []

        #loop if multiple invoices
        for invoice in sale_order.invoice_ids:
            #Sum of payments created in all invoices
            existing_payment_amount += invoice.amount_total - invoice.amount_residual

            #Variable will be used to compare cancelled invoice payments and created new invoices
            existing_invoices.append(invoice)

            #If invoice not reversed, proceed with refund and credit note return payment
            if invoice.payment_state != 'reversed':

                #Void payments first to remove payment_state 'paid' and 'in_payment'
                payments = json.loads(invoice.invoice_payments_widget)
                if payments != False:
                    for payment in payments['content']:
                        void = self.env['account.payment'].search([('id','=',payment['account_payment_id'])])
                        void.action_draft()
                        void.action_cancel()

                #Use the refund wizard existing in Odoo ORM
                refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.id).create({
                    'reason': params['name'] + ': Edited by CircuitTrack',
                    'refund_method': 'refund' if invoice.payment_state in ['paid','in_payment'] else 'cancel',
                    'date_mode': 'custom',
                    'date': date_order
                })
                refund_wizard.reverse_moves()

                # #CREDIT NOTE WIDGET STANDBY
                # if invoice.payment_state != 'reversed':
                #     #Post Credit Note
                #     credit_note = refund_wizard.new_move_ids
                #     credit_note.write({'invoice_date': date_order})
                #     credit_note.action_post()

                #     #Create a payment in Credit Note
                #     credit_note_payment = invoice.env['account.payment.register'].with_context({
                #         "active_model": "account.move",
                #         "active_ids": credit_note.id
                #     }).create([{
                #         "payment_date": date_order,
                #         "amount": invoice.amount_total,
                #         "journal_id": sale_order.payment_journal_id.id,
                #         "payment_method_id": 1,
                #         "company_id": sale_order.company_id.id
                #     }])
                #     credit_note_payment.action_create_payments()

                #     #Log a note in the cancelled invoice
                #     log_note += " - Reverse Entry: " + credit_note.name

                log_note += " - Reverse Entry: " + refund_wizard.new_move_ids.name

            #Log a note in the cancelled invoice
            invoice.message_post(body=log_note)
            invoice.write({
                'name': invoice.name + '-cancelled'
            })

        #Cancel previous invoice to create new amended invoice
        sale_order.action_cancel()

        #Log a note in the cancelled Sale Order    
        sale_order.message_post(body=log_note)

        #Rename previous sale order to avoid unique_constraints
        sale_order_ids = self.env['sale.order'].search([('name','like',params['name'] + '-cancelled')])
        cancel_count = len(sale_order_ids)
        appended = '-cancelled-' + str(cancel_count) if cancel_count > 0 else '-cancelled'
        sale_order.sudo().write({"name": params['name'] + appended})

        #Create the revised  Sales Order and Invoice if no void or void=True
        if 'void' not in params:
            params['void'] = False

        if params['void'] != True:
            #Check for required Keys
            for key in ['payment_amount']:
                if key not in params:
                    raise ValidationError(_("%s is required with {void = False}",key))
            
            #delete void params as it is not needed in _create_sale_order function
            params.pop('void')

            #Commit and save all the code run progress before creating Sales Order to avoid unique constraints
            sale_order.env.cr.commit()

            #Create New Sale Order
            revised_sale_order_return = self._create_sale_order(params)

            # #Assign Outstanding payment from previous invoices to the newly created invoices in the sales order
            # revised_sale_order = self.env['sale.order'].browse(revised_sale_order_return['id'])
            # for invoice in revised_sale_order.invoice_ids:

            #     #Convert the JSON Value from the payment widget(invoice_outstanding_credits_debits_widget) to confirm outstanding payment to new invoice
            #     pending_payments = json.loads(invoice.invoice_outstanding_credits_debits_widget)
            #     if pending_payments['content']:
            #         for i in pending_payments['content']:
            #             if i['journal_name'] in existing_invoices:
            #                 invoice.js_assign_outstanding_line(i['id'])

            return revised_sale_order_return
        return {"void": True}

    def _create_sale_order(self,values):
        #check shipper_id to sync with CircuitTrack
        if 'shipper_id' in values:
            if 'partner_id' in values:
                raise ValidationError("Do not use both 'shipper_id' and 'partner_id'")
            if values['shipper_id']:
                created_partner = self.env['cbiz.api.cargoapi'].cargo_sync_shipper(values['shipper_id'])
                values['partner_id'] = created_partner.id

        if 'shipper_details' in values:
            if 'shipper_id' in values or 'partner_id' in values:
                raise ValidationError("Do not use both 'shipper_id' and 'partner_id' with shipper_details")
            created_partner = self.env['res.partner'].search([('name','=',values['shipper_details']['name'])])
            if not created_partner:
                created_partner = self.env['res.partner'].create({
                    "name": values['shipper_details']['name'],
                    "phone": values['shipper_details']['phone'],
                    "vat": values['shipper_details']['vat'],
                    "email": "cargo_v1@imerex.com.ph"
                })
            values['partner_id'] = created_partner.id
                

        #use cargo_branch_id to search for branch_id which is required by sale order
        if 'cargo_branch_id' in values:
            values['branch_id'] = self.env['res.branch'].search([('cargo_branch_id','=',values['cargo_branch_id'])]).id
            if not values['branch_id']:
                raise ValidationError('No Branch with the given Cargo ID')

        #default value for company_id
        if 'company_id' not in values:
            values['company_id'] = 1

        #Check if company has branches or not
        if 'branch_id' not in values:
            test_branch_in_company = self.env['res.branch'].search([('company_id','=',values['company_id'])]).ids
            if test_branch_in_company:
                raise ValidationError('Branch is required in the given Company!')

        #Default bank journal ID of company
        if 'payment_journal_id' not in values:
            default_id = self.env['account.journal'].search([('company_id','=',values['company_id']),('type','=','cash'),('name','like','Head Office')]).ids
            values['payment_journal_id'] = default_id[0]

        sale_order_fields = self._sale_order_fields()
        sale_order_values = {}

        #convert from local TZ to UTC
        values['date_order'] = self._time_store(values['date_order'])

        #serialize order fields except for order_line
        for order_data in sale_order_fields:
            if order_data in values:
                if not order_data == 'order_line':
                    sale_order_values.update({
                            order_data: values[order_data]
                        })

        #create sales order without orderline
        created_sale_order = self.env['sale.order'].create(sale_order_values)

        #create sales order_line and attach to sales order
        sale_order_line_fields = self._sale_order_line_fields()

        #serialize order_line fields
        for order_line_item in values['order_line']:
            order_line_values={}
            order_line_item_name = False
            if 'code' in order_line_item:
                order_line_item['product_id'] = self.env['product.template'].search([('code','=',order_line_item['code'])]).id
            if 'id' in order_line_item:
                order_line_item['product_id'] = self.env['product.template'].browse(int(order_line_item['id'])).id
            if 'product_uom_qty' not in order_line_item:
                order_line_item['product_uom_qty'] = 1
            if 'description' in order_line_item:
                if order_line_item['description']:
                    order_line_item_name = order_line_item.pop('description')
                else:
                    order_line_item.pop('description')
            for order_line_data in sale_order_line_fields:
                if order_line_data in order_line_item:
                    order_line_values.update({
                        order_line_data: order_line_item[order_line_data]
                    })
            order_line_values.update({
                "order_id": created_sale_order.id
            })
            created_sale_order_lines = self.env['sale.order.line'].create(order_line_values)
            if order_line_item_name:
                created_sale_order_lines.update(
                    {"name": order_line_item_name}
                )
        #confirm the sales_order
        created_sale_order.action_confirm()
        #get return value to dict instead of model
        return_sale_order = self._return_create_values(created_sale_order)
        return return_sale_order


    def _validator_create(self):
        schema = {
            "code": {"type": "string"},
            "id": {},
            "product_uom_qty": {"type": "float"},
            "price_unit": {"type": "float"},
            "description": {
                "type": "string",
                "empty": True,
                "nullable": True
            }
        }
        shipper_schema = {
            "name": {"type":"string", "required":True},
            "phone": {"type":"string", "required": True},
            "vat": {"type":"string", "required": True, "nullable": True}
        }
        res = {
            "name":{
                "type": "string",
                "required": True
            },
            "shipper_id":{},
            "date_order":{},
            "shipper_details":{
                "required": False,
                "empty": True,
                "type": "dict",
                },
            "partner_id":{"type": "integer"},
            "company_id": {"type": "integer"},
            "cargo_branch_id":{"type": "integer"},
            "payment_journal_id":{"type": "float"},
            "payment_amount":{"type": "float"},
            "client_order_ref": {"type": "string"},
            "order_line": {
                "type": "list",
                "schema": {"type": "dict", "schema": schema},
            },
        }
        return res

    def _validator_amendments(self):
        res = self._validator_create()
        res.update({
            "void": {"type": "boolean"}
        })
        return res


    def _validator_return_create(self):
        res = {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "invoice_id": {"type": "integer"},
        }
        return res

    def _validator_return_amendments(self):
        res = self._validator_return_create()
        res.update({
            "void": {"type": "boolean"}
        })
        return res

    def _sale_order_fields(self):
        cbiz_fields = [
            "name",
            "shipper_id",
            "date_order",
            "partner_id",
            "company_id",
            "branch_id",
            "payment_journal_id",
            "payment_amount",
            "order_line",
            ]
        return cbiz_fields

    def _time_store(self, order_date):
        #convert from local to utc as Odoo framework stores date in UTC for easy conversion
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        #convert string to datetime format for local time
        date_order = user_tz.localize(fields.Datetime.from_string(order_date))
        #change timezone to UTC
        date_order_utc = date_order.astimezone(pytz.timezone('UTC'))
        #bring the converted value back to the dict with key date_order
        return fields.Datetime.to_string(date_order_utc)

    def _sale_order_line_fields(self):
        cbiz_fields = [
            "product_id",
            "product_uom_qty",
            "price_unit",
            "description"
            ]
        return cbiz_fields

    def _return_create_values(self,created_order):
        return_sale_order = {
            "id": created_order.id,
            "name": created_order.name,
            "invoice_id": created_order.invoice_ids.id
        }
        return return_sale_order