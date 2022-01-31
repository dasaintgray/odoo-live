# See LICENSE file for full copyright and licensing details.
"""Module For City."""

from odoo import api, fields, models, exceptions
from odoo.tools.misc import unique
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"
    hashrow = fields.Char("HashRow", size=64)

class AccountMove(models.Model):
    _inherit = "account.move"
    hashrow = fields.Char("HashRow", size=64)
    hashrow_pay = fields.Char("HashRowPay", size=64)
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    hashrow = fields.Char("HashRow", size=64)