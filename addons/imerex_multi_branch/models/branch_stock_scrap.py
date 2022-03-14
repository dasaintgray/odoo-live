# -*- coding: utf-8 -*-
# Part of Odoo. See ICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    # branch_id = fields.Many2one("res.branch", string='Branch')

    # def action_validate(self):
    #     res = super(StockScrap, self).action_validate()
    #     if self.picking_id.branch_id:
    #         return_picking = self.env['stock.picking'].browse(res['res_id'])
    #         return_picking.write({
    #             "branch_id": self.picking_id.branch_id.id
    #         }) 
    #     return res
