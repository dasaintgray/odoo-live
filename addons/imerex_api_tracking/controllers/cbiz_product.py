
from odoo import http, _
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from odoo.http import request
from odoo.exceptions import ValidationError
import base64
from odoo.modules import get_module_resource
from addons.web.controllers.main import Binary

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
        [(['/mobile','/mobile/<string:code>'], "GET")],
        input_param=restapi.CerberusValidator("_validator_mobile")
        )
    def mobile(self,cargo_branch_id=False,company_id=2, **kwargs):

        """
        Product QTY by Code and Branch ID
        """
        #Search Branch with the given cargo_branch_id
        branch = self.env['res.branch'].search([('cargo_branch_id','=',cargo_branch_id)])

        #Check if there is a valid branch with given cargo_branch_id and search warehouse Locations using the branch ID
        if not branch:
            #Create an empty string appended_psql_query for Postgresql query exection
            appended_psql_query = """"""
            #Get all stock locations from warehouse
            location = self.env['stock.warehouse'].search([]).lot_stock_id
        else:
            #Stringify list of ids in the branch for postgresql query consumption
            branch_ids = ", ".join(repr(id) for id in branch.ids)
            #Create a Postgresl query execution and filter for branch ID
            appended_psql_query = _("""
            LEFT JOIN
            (SELECT
            product_template_res_branch_rel.product_template_id AS id,
            res_branch.receipt_branchname
            FROM
            product_template_res_branch_rel
            LEFT JOIN
            res_branch
            ON
            product_template_res_branch_rel.res_branch_id = res_branch.id
            WHERE
            res_branch.id IN (%(branch_id)s))
            table_branch
            ON
            table_product.id = table_branch.id
            """,branch_id=branch_ids)
            #Get the stock location from stock warehouse with given branch id
            location = self.env['stock.warehouse'].search([('branch_id','=',branch.ids)]).lot_stock_id

        #Create a list of Product IDs in order to merge them with given parameters.
        if 'code' in kwargs:
            #if a comma is detected on the string, convert string to list
            if ',' in kwargs['code']:
                codes = kwargs['code'].split(',') 
                search_ids = self.env['product.template'].search([("code","in",codes)])
            elif '|' in kwargs['code']:
                codes = kwargs['code'].split('|') 
                search_ids = self.env['product.template'].search([("code","in",codes)])
            else:
                #if code is singleton without delimiter
                search_ids = self.env['product.template'].search([("code","=",kwargs['code'])])
        else:
            #If no given code, initialize product template ids for search_ids
            search_ids = self.env['product.template'].search([])

        #<-- Insert New Code Block Parameter here with list(set(A)&set(search_ids)) --> 

        #Check if there are items with all given parameters
        if not search_ids:
            raise ValidationError("No Product Found")

        #Initialize return values
        return_value=[]
        #Initialize base_url
        base_url = self.env['ir.config_parameter'].get_param('web.base.url').replace('http://','https://')

        #Stringify list of product_ids and location_ids in the branch for postgresql query consumption
        product_ids = ", ".join(repr(id) for id in search_ids.ids)
        location_ids = ", ".join(repr(id) for id in location.ids)

        #Query full table data from database
        self.env.cr.execute(_("""
            SELECT * FROM
            ((SELECT
            product_template.id,
            product_template.default_code,
            product_template.code,
            product_template.name,
            product_template.description_sale,
            product_template.list_price
            FROM product_template
            WHERE product_template.id IN (%(product_ids)s))
            table_product
            LEFT JOIN
            (SELECT
            stock_quant.product_id,
            SUM(stock_quant.quantity) as quantity
            FROM stock_quant
            WHERE stock_quant.location_id in (%(location_id)s) GROUP BY stock_quant.product_id)
            table_stock_quant
            ON table_product.id = table_stock_quant.product_id
            LEFT JOIN
            (SELECT
            product_taxes_rel.prod_id as id,
            account_tax.amount_type,
            account_tax.amount,
            account_tax.price_include
            FROM product_taxes_rel
            LEFT JOIN account_tax
            ON product_taxes_rel.tax_id = account_tax.id
            WHERE account_tax.company_id = %(company_id)s)
            table_tax
            ON table_product.id = table_tax.id
            LEFT JOIN
            (SELECT
            sale_order_line.product_id,
            SUM(sale_order_line.product_uom_qty) AS sold
            FROM sale_order_line
            GROUP BY sale_order_line.product_id)
            table_count
            ON table_product.id = table_count.product_id
            %(appended_psql_query)s
            )
            AS products
            ORDER BY COALESCE(products.sold,0) DESC
        """,
        product_ids=product_ids,
        location_id=location_ids,
        appended_psql_query=appended_psql_query,
        company_id=company_id))

        #fetch catched query reponse
        data = self.env.cr.fetchall()

        #get company currency
        currency = self.env['res.company'].browse(company_id).currency_id.symbol

        #Loop and serialize data in to a list
        for i in data:
            #Check for tax and compute price based on tax data
            if i[9]:
                if i[9]=='percent' and not i[11]:
                    price = i[5] + (i[10]*i[5]/100)
                else:
                    price = i[5] + i[10]
            else:
                price = i[5]
            #Create a dict to add in a list
            datarow={
                "id":i[0],
                "default_code":i[1] or '',
                "code":i[2] or '',
                "name":i[3] or '',
                "description":i[4] or '',
                "price": price or 0,
                "qty":i[7] or 0,
                "currency":currency or False,
                "branch": i[15] if 15 < len(i) else '',
                "salescount": i[13] or 0,
                'image_url_128': base_url + "/product/image_128/" + str(i[0]),
                'image_url_256': base_url + "/product/image_256/" +str(i[0]),
                'image_url_512': base_url + "/product/image_512/" + str(i[0])
            }
            return_value.append(datarow)
        return return_value

    def _validator_mobile(self):
        return {
            "cargo_branch_id": {"type": "integer", "required": False},
            "company_id": {"type": "string", "required": False},
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


class ProductController(http.Controller):
    _description="""Product New Controller """        
        
    @http.route(['/product/<string:image_str>/<int:seq>'], type='http', auth="api_key", website=True)
    def product_download_image(self, image_str, seq,**kwargs):
        return Binary.content_image(self, xmlid=None, model='ir.attachment', id=seq, field=image_str,
                      filename_field='name', unique=None, filename=None, mimetype=None,
                      download=None, width=0, height=0, crop=False, access_token=None, quality=int(kwargs.get('quality', 0)))
    

    