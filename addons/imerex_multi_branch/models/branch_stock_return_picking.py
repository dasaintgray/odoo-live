# -*- coding: utf-8 -*-
# Part of Odoo. See ICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        res = super(ReturnPicking, self).create_returns()
        if self.picking_id.branch_id:
            return_picking = self.env['stock.picking'].browse(res['res_id'])
            return_picking.write({
                "branch_id": self.picking_id.branch_id.id
            }) 
        return res
