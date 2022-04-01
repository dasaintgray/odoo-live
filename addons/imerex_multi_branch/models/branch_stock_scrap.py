# -*- coding: utf-8 -*-
# Part of Odoo. See ICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    @api.model
    def _get_branch_id(self):
        domain_return = ['&',('id', 'in',self.env.user.branch_ids.ids),('company_id','=',self.env.company.id)]
        return domain_return

    branch_id = fields.Many2one("res.branch", string='Branch',default=lambda self: self.branch_id.search(self._get_branch_id()),domain=_get_branch_id)

    def action_validate(self):
        if self.picking_id.branch_id:
            self.branch_id = self.picking_id.branch_id 
        res = super(StockScrap, self).action_validate()
        return res

    @api.depends('branch_id')
    @api.onchange('branch_id')
    def domain_location_id(self):
        company = self.company_id.id
        warehouse = self.env['stock.warehouse'].search([('branch_id','=',self.branch_id.id)]).lot_stock_id.ids
        domain_return = ['&',('company_id','=', company),'&',('usage', '=','internal'),('id','=',warehouse)]
        self.location_id = self.location_id.search(domain_return).id
        return {'domain': {
            'location_id': domain_return,
            }}
        