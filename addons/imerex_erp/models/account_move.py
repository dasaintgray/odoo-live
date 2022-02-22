# See LICENSE file for full copyright and licensing details.
"""Module For City."""

from odoo import api, fields, models, exceptions
from odoo.tools.misc import unique
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = "account.move"
    _sql_constraints = [('ref_unique', 'unique(ref)','Reference must be unique!')]