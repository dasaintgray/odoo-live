
from odoo import fields, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from datetime import datetime,timedelta

from odoo.exceptions import ValidationError
class cBizProductService(Component):
    _inherit = "base.rest.service"
    _name = "cbiz.product.service"
    _usage = "product"
    _collection = "cbiz.services.api"
    _description = """
        Product API Service

        Service used to search Products
    """

    @restapi.method(
        [(['/<int:id>'], "GET")],
        output_param=restapi.CerberusValidator("_validator_return_get")
        )
    def get(self, id):
        """
        Search Product by ID
        """
        search_ids = self.env['product.template'].search([("id","=",id)]).ids
        if not search_ids:
            raise ValidationError("No Product Found")
        final_search = self.env['product.template'].search([("id","=",search_ids)])
        return_value = {}
        for id in final_search.ids:
            return_value.update(self._return_product_values(id))
        return return_value

    @restapi.method(
        [(['/search'], "GET")],
        input_param=restapi.CerberusValidator("_validator_search"),
        )
    def search(self,name='',code=''):
        """
        Search Product by Name
        """
        search_ids = self.env['product.template'].search([]).ids
        if name:
            search_ids = self.env['product.template'].search([("|"),("name","like",name),("default_code","=",name)]).ids
        if code:
            if ',' in code:
                codes = code.split(',')
                search_code = self.env['product.template'].search([("code","in",codes)]).ids
            else:
                search_code = self.env['product.template'].search([("code","=",code)]).ids
            search_ids = list(set(search_code)&set(search_ids))
        if not search_ids:
            raise ValidationError("No Product Found")
        final_search = self.env['product.template'].search([("id","=",search_ids)])
        return_value = []
        for id in final_search.ids:
            return_value.append(self._return_product_values(id))
        return return_value

    @restapi.method(
        [(['/code/'], "GET")],
        input_param=restapi.CerberusValidator("_validator_code"),
        output_param=restapi.CerberusValidator("_validator_return_code")
        )

    def code(self,code=''):
        """
        Search Product by Code
        """
        search_id = self.env['product.template'].search([("code","=",code)]).id
        product = self._return_product_values(search_id)
        return product

    @restapi.method(
        [(['/qty/'], "GET")],
        input_param=restapi.CerberusValidator("_validator_qty")
        )
    def qty(self,cargo_branch_id,code=''):
        """
        Product QTY by Code
        """
        branch = self.env['res.branch'].search([('cargo_branch_id','=',cargo_branch_id)])
        if not branch:
            raise ValidationError("No Branch with given Cargo ID")
        location = self.env['stock.warehouse'].search([('branch_id','=',branch.ids)]).view_location_id
        quantity = self.env['stock.quant']
        if code:
            search_ids = self.env['product.template'].search([("code","=",code)]).ids
        else:
            search_ids = self.env['product.template'].search([]).ids
        if not search_ids:
            raise ValidationError("No Product Found")
        final_search = self.env['product.template'].search([("id","=",search_ids)])
        return_value=[]
        for id in final_search.ids:
            product = self.env['product.template'].browse(id)
            qty_available = quantity._get_available_quantity(product, location)
            details = {}
            details.update({
                'id': product.id,
                'code': product.code,
                'name': product.display_name,
                'qty': qty_available,
                'branch': branch.receipt_branchname
            })
            return_value.append(details)
        return return_value

    #ADD BY HENRY MEMPIN/Edited by James Tecson
    #DATE: 28 MARCH 2022
    #TIME: 14:08
    #PURPOSE: For Mobile Consumer
    ##################################################################################################################
    @restapi.method(
        [(['/mobile/'], "GET")],
        input_param=restapi.CerberusValidator("_validator_mobile")
        )
    def mobile(self,cargo_branch_id=False,code=''):
        """
        Product QTY by Code and Branch ID
        """
        #Search Branch with the given cargo_branch_id
        branch = self.env['res.branch'].search([('cargo_branch_id','=',cargo_branch_id)])

        #Search Warehouse Locations using the branch ID
        location = self.env['stock.warehouse'].search([('branch_id','=',branch.ids)]).view_location_id

        #Create a list of IDs in order to merge them with given parameters.
        #This code block is created just in case additional parameters are added
        if code:
            #if a comma is detected on the string, convert string to list
            if ',' in code:
                codes = code.split(',') 
                search_ids = self.env['product.template'].search([("code","in",codes)]).ids
            else:
                #if code is singleton without delimiter
                search_ids = self.env['product.template'].search([("code","=",code)]).ids
        else:
            #If no given code, initialize product template ids for search_ids
            search_ids = self.env['product.template'].search([]).ids

        #<-- Insert New Code Block Parameter here with list(set(A)&set(search_ids)) --> 

        #Check if there are items with all given parameters
        if not search_ids:
            raise ValidationError("No Product Found")

        
        final_search = self.env['product.template'].search([("id","in",search_ids)])
        return_value=[]

        base_url = self.env['ir.config_parameter'].get_param('web.base.url').replace('http://','https://') + "/web/image/product.template/"
        for id in final_search.ids:
            product = self.env['product.product'].browse(id)

            #If location found, system will use warehouse, else system will use all
            if location:
                qty_available = self.env['stock.quant']._get_available_quantity(product,location)
            else:
                qty_available = product.qty_available
    
            #Search for tax to compute, temporarily hardcoded, however needed to be adjusted if multiple sales tax are included
            tax = product.taxes_id.search([('company_id','=',2),('type_tax_use','=','sale')],limit=1)

            #Compute Total with Tax with given Parameter
            orderline = self.env['sale.order.line'].new({
                'product_template_id': product.id,
                'price_unit': product.list_price,
                'tax_id': tax
            })

            #Create a dict of the product details
            details = {
                'id': product.id,
                'code': product.code or '',
                'name': product.name,
                'display_name': product.display_name,
                'qty': qty_available,
                'sales_count': product.sales_count,
                'price': orderline.price_unit + orderline.price_tax,
                'currency': product.currency_id.display_name,
                'branch': branch.receipt_branchname or '',
                'description': product.description_sale or '',
                'image_url_128': base_url + str(id) + "/image_128",
                'image_url_256': base_url + str(id) + "/image_256",
                'image_url_512': base_url + str(id) + "/image_512"
            }

            #List all appended values from details
            return_value.append(details)
        return return_value

    def _validator_mobile(self):
        return {
            "cargo_branch_id": {"type": "string", "required": False},
            "code": {"type": "string", "required": False, "nullable": True}
        }

    def _validator_code(self):
        return {
            "code": {"type": "string", "required": False, "nullable": True}
        }

    def _validator_return_code(self):
        return_code = self._validator_return_get()
        return return_code

    def _validator_return_get(self):
        return {
            "id": {"type": "integer"},
            "code":{"type": "string"},
            "name":{"type": "string"},
            "description": {"type":"string"},
            "qty": {"type":"float"},
            "image": {"type":"string"},
        }

    def _validator_search(self):
        return {
            "code":{"type": "string", "required": False},
            "name":{"type": "string", "required": False},
            "branch":{"type": "string", "required": False},              
        }
       
    def _return_product_values(self,id):
        product = self.env['product.template'].browse(id)
        image = self._http_image(id)
        return {
            "id": product.id,
            "code": product.code or '',
            "name": product.display_name,
            "description": product.description_sale or '',
            "image": image,
        }

    def _http_image(self,id):
        status,headers,image = self.env["ir.http"].binary_content(
            model="product.template", id=id, field="image_1920"
        )
        if isinstance(image,bytes):
            image_string = "data:image;base64," + image.decode('utf-8')
        else:
            image_string = "data:image;base64," + image
        if image_string == "data:image;base64,":
            image_string = ''
        return image_string