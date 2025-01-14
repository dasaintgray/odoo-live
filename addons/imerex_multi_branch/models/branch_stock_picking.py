# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    """inherited stock.picking"""
    _inherit = "stock.picking"

    @api.model
    def _get_branch_id(self):
        domain_return = ['&',('id', 'in',self.env.user.branch_ids.ids),('company_id','=',self.env.company.id)]
        return domain_return
    
    branch_id = fields.Many2one("res.branch", string='Branch', store=True,
                                readonly=False,
                                compute="_compute_branch",
                                domain=_get_branch_id
                                ) 
    branch_location_ids = fields.Many2many("res.branch", string='Branch IDs',compute="_compute_location_branch",store=True)

    @api.onchange('picking_type_id')
    def change_location_dest_id(self):
        if self.picking_type_id.code == 'internal':
            warehouse = self.env['stock.warehouse'].search([('branch_id','=',self.env.user.branch_ids.ids),('branch_id','!=',self.branch_id.id)]).lot_stock_id
            if len(warehouse) > 1:
                self.picking_type_id.default_location_dest_id = warehouse[0]
            else:
                self.picking_type_id.default_location_dest_id = warehouse

    @api.onchange('picking_type_id')
    def domain_location_id(self):
        company = self.env.company.id
        if self.picking_type_id.code == 'outgoing':
            warehouse = self.env['stock.warehouse'].search([('branch_id','=',self.branch_id.id)]).lot_stock_id.ids
            domain_return = ['&',('company_id','=', company),'&',('usage', '=','internal'),('id','=',warehouse)]
        elif self.picking_type_id.code == 'internal':
            warehouse = self.env['stock.warehouse'].search([('branch_id','=',self.branch_id.id)]).lot_stock_id.ids
            domain_return = ['&',('company_id','=', company),'&',('usage', '=','internal'),('id','in',warehouse)]
        else:
            domain_return = ['&',('company_id','=', company),('usage', '=','internal')]
        return {'domain': {'location_id': domain_return}}

    @api.onchange('picking_type_id')
    def domain_location_dest_id(self):
        company = self.env.company.id
        if self.picking_type_id.code == 'incoming':
            warehouse = self.env['stock.warehouse'].search([('branch_id','=',self.branch_id.id)]).lot_stock_id.ids
            domain_return = ['&',('company_id','=', company),'&',('usage', '=','internal'),('id','=',warehouse)]
        elif self.picking_type_id.code == 'internal':
            warehouse = self.env['stock.warehouse'].search([('branch_id','=',self.env.user.branch_ids.ids),('branch_id','!=',self.branch_id.id)]).lot_stock_id.ids
            if not warehouse:
                warehouse = self.env['stock.warehouse'].sudo().search([('company_id','=',self.env.company.id),('branch_id','!=',self.branch_id.id)]).lot_stock_id.ids
            domain_return = ['&',('company_id','=', company),'&',('usage', '=','internal'),('id','in',warehouse)]
            self.location_dest_id = warehouse[0]

        else:
            domain_return = ['&',('company_id','=', company),('usage', '=','internal')]
        return {'domain': {'location_dest_id': domain_return}}

    @api.depends('location_id', 'location_dest_id')
    def _compute_location_branch(self):
        warehouse_branches = self.env['stock.warehouse'].search([('|'),('lot_stock_id','=',self.location_id.id),('lot_stock_id','=',self.location_dest_id.id)]).branch_id.ids
        self.branch_location_ids = warehouse_branches

    @api.depends('sale_id', 'purchase_id')
    def _compute_branch(self):
        for order in self:
            so_company = order.company_id if order.company_id else self.env.company
            branch_ids = self.env.user.branch_ids
            branch = branch_ids.filtered(
                lambda branch:
                    branch.id == self.env.user.branch_id.id and
                    branch.company_id == so_company
                    if self.env.user.branch_id
                    else branch.company_id == so_company
                )
            if branch:
                order.branch_id = branch.ids[0]
            # else:
            #     if order.branch_id:
            #         order.branch_id = False
            if order.sale_id or order.purchase_id:
                if order.sale_id.branch_id:
                    order.branch_id = order.sale_id.branch_id
                if order.purchase_id.branch_id:
                    order.branch_id = order.purchase_id.branch_id

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        """onchange methode"""
        self.picking_type_id = False
        self.location_id = False
        self.location_dest_id = False

    @api.depends('sale_id', 'purchase_id')
    def _compute_branch_id(self):
        """methode to compute branch"""
        for record in self:
            record.branch_id = False
            if record.sale_id.branch_id:
                record.branch_id = record.sale_id.branch_id
            if record.purchase_id.branch_id:
                record.branch_id = record.purchase_id.branch_id


class StockPickingTypes(models.Model):
    """inherited stock picking type"""
    _inherit = "stock.picking.type"

    branch_id = fields.Many2one('res.branch', string='Branch', store=True,
                                related='warehouse_id.branch_id')
