
from odoo import fields, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from odoo.exceptions import ValidationError

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
        created_sale_order = self._create_sale_order(params)
        return created_sale_order

    def _create_sale_order(self,values):
        if 'shipper_id' in values:
            if 'partner_id' in values:
                raise ValidationError("Do not use both 'shipper_id' and 'partner_id'")
            if values['shipper_id']:
                created_partner = self.env['cbiz.api.cargoapi'].cargo_sync_shipper(values['shipper_id'])
                values['partner_id'] = created_partner.id
                # values['partner_invoice_id'] = created_partner.id
                # values['partner_shipping_id'] = created_partner.id
        if 'cargo_branch_id' in values:
            values['branch_id'] = self.env['res.branch'].search([('cargo_branch_id','=',values['cargo_branch_id'])]).id
            if not values['branch_id']:
                raise ValidationError('No Branch with the given Cargo ID')
        if 'company_id' not in values:
            values['company_id'] = 1
        if 'branch_id' not in values:
            test_branch_in_company = self.env['res.branch'].search([('company_id','=',values['company_id'])]).ids
            if test_branch_in_company:
                raise ValidationError('Branch is required in the given Company!')
        if 'payment_journal_id' not in values:
            default_id = self.env['account.journal'].search([('company_id','=',values['company_id']),('type','=','bank')]).ids
            values['payment_journal_id'] = default_id[0] 
        sale_order_fields = self._sale_order_fields()
        sale_order_values={}
        values['date_order'] = fields.Datetime.from_string(values['date_order'])
        for order_data in sale_order_fields:
            if order_data in values:
                if not order_data == 'order_line':
                    sale_order_values.update({
                            order_data: values[order_data]
                        })
        created_sale_order = self.env['sale.order'].create(sale_order_values)

        sale_order_line_values=[]
        sale_order_line_fields = self._sale_order_line_fields()
        for order_line_item in values['order_line']:
            order_line_values={}
            if 'code' in order_line_item:
                order_line_item['product_id'] = self.env['product.template'].search([('code','=',order_line_item['code'])]).id
            if 'product_uom_qty' not in order_line_item:
                order_line_item['product_uom_qty'] = 1
            for order_line_data in sale_order_line_fields:
                order_line_values.update({
                    order_line_data: order_line_item[order_line_data]
                })
            order_line_values.update({
                "order_id": created_sale_order.id
            })
            created_sale_order_lines = self.env['sale.order.line'].create(order_line_values)
            sale_order_line_values.append({
                created_sale_order_lines
            })
        created_sale_order.action_confirm()
        return_sale_order = self._return_create_values(created_sale_order)
        return return_sale_order

    def _validator_create(self):
        schema = {
            "code": {"type": "string"},
            "product_uom_qty": {"type": "float"},
            "price_unit": {"type": "float"}
        }
        res = {
            "name":{
                "type": "string",
                "required": True
            },
            "shipper_id":{},
            "date_order":{},
            "partner_id":{"type": "integer"},
            "company_id": {"type": "integer"},
            "cargo_branch_id":{"type": "integer"},
            "payment_journal_id":{"type": "float"},
            "payment_amount":{"type": "float"},
            "client_order_ref": {"type": "string"},
            "order_line": {
                "type": "list",
                "required": True,
                "schema": {"type": "dict", "schema": schema},
            },
        }
        return res

    def _validator_return_create(self):
        res = {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "invoice_id": {"type": "integer"},
        }
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

    def _sale_order_line_fields(self):
        cbiz_fields = [
            "product_id",
            "product_uom_qty",
            "price_unit",
            ]
        return cbiz_fields

    def _return_create_values(self,created_order):
        return_sale_order = {
            "id": created_order.id,
            "name": created_order.name,
            "invoice_id": created_order.invoice_ids.id
        }
        return return_sale_order
