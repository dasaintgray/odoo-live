import logging
from datetime import timedelta
from functools import partial

import psycopg2
import pytz
import re

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero, float_round
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
from odoo.osv.expression import AND
import base64

class PosOrder(models.Model):
    _inherit = "pos.order"
    _description = "Point of Sale Orders"
    _order = "date_order desc, name desc, id desc"

    branch_id = fields.Many2one("res.branch", string='Branch', store=True,
                                readonly=True)
    @api.model
    def _order_fields(self, ui_order):
        override = super(PosOrder, self)._order_fields(ui_order)
        override['branch_id'] = self.env['pos.session'].browse(ui_order['pos_session_id']).branch_id.id
        return override

    def _prepare_invoice_vals(self):
        to_invoice_override = super(PosOrder,self)._prepare_invoice_vals()
        to_invoice_override['branch_id'] = self.config_id.branch_id.id
        return to_invoice_override