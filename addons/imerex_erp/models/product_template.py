# See LICENSE file for full copyright and licensing details.
"""Module For City."""

from odoo import api, fields, models, exceptions
from odoo.tools.misc import unique
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    code = fields.Char("Cargo Code")