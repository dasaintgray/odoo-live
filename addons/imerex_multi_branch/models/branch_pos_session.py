# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare

class PosSession(models.Model):
    _inherit = 'pos.session'

    branch_id = fields.Many2one("res.branch", string='Branch')

    @api.model
    def create(self, values):
        #session creation add branch_id
        session_override = super(PosSession, self).create(values)
        session_override.branch_id = session_override.config_id.branch_id
        return session_override

    def write(self,vals):
        pos_session_override = super(PosSession,self).write(vals)
        if 'move_id' in vals:
            #add branch id on account move/journal
            self.move_id.branch_id = self.branch_id.id
        return pos_session_override
    
    def _create_cash_statement_lines_and_cash_move_lines(self, vals):
        pos_session_override = super(PosSession,self)._create_cash_statement_lines_and_cash_move_lines(vals)
        #add branch id on cash journals
        if 'split_cash_statement_lines' in vals:
            if pos_session_override['split_cash_statement_lines'][self.cash_register_id]['id']:
                pos_session_override['split_cash_statement_lines'][self.cash_register_id]['branch_id'] = self.branch_id.id
        if 'combine_cash_statement_lines' in vals:
            if pos_session_override['combine_cash_statement_lines'][self.cash_register_id]['id']:
                pos_session_override['combine_cash_statement_lines'][self.cash_register_id]['branch_id'] = self.branch_id.id      
        if 'split_cash_receivable_lines' in vals:
            if pos_session_override['split_cash_receivable_lines'][self.cash_register_id]['id']:
                pos_session_override['split_cash_receivable_lines'][self.cash_register_id]['branch_id'] = self.branch_id.id
        if 'combine_cash_receivable_lines' in vals:
            if pos_session_override['combine_cash_receivable_lines'][self.cash_register_id]['id']:
                pos_session_override['combine_cash_receivable_lines'][self.cash_register_id]['branch_id'] = self.branch_id.id
        return pos_session_override