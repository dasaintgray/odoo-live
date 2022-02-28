from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero, float_round
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
from odoo.osv.expression import AND

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    pos_name = fields.Char("Name in POS Receipt")
    branch_id = fields.Many2one("res.branch", string='Branch', store=True)
