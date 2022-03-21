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

    def open_cashbox_pos(self):
        if not self.statement_ids.cashbox_end_id.cashbox_lines_ids:
            for value in [0.25,0.50,1.00,2.00,5,10,20,50,100,200,500]:
                vals = {
                    'cashbox_id': self.statement_ids.cashbox_end_id.id,
                    'number': 0,
                    'coin_value': value
                }
                cashbox_lines_ids = self.env['account.cashbox.line'].create(vals)
        open_cashbox_pos_override = super(PosSession,self).open_cashbox_pos()
        return open_cashbox_pos_override

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
            if self.cash_register_id in pos_session_override['split_cash_statement_lines']:
                pos_session_override['split_cash_statement_lines'][self.cash_register_id]['branch_id'] = self.branch_id.id
        if 'combine_cash_statement_lines' in vals:
            if self.cash_register_id in pos_session_override['combine_cash_statement_lines']:
                pos_session_override['combine_cash_statement_lines'][self.cash_register_id]['branch_id'] = self.branch_id.id      
        if 'split_cash_receivable_lines' in vals:
            if self.cash_register_id in pos_session_override['split_cash_receivable_lines']:
                pos_session_override['split_cash_receivable_lines'][self.cash_register_id]['branch_id'] = self.branch_id.id
        if 'combine_cash_receivable_lines' in vals:
            if self.cash_register_id in pos_session_override['combine_cash_receivable_lines']:
                pos_session_override['combine_cash_receivable_lines'][self.cash_register_id]['branch_id'] = self.branch_id.id
        return pos_session_override