from odoo import api, fields, models, exceptions
from odoo.tools.misc import unique
from odoo.exceptions import UserError,ValidationError

class SaleOrder(models.Model):

    _inherit = "sale.order"
    date_order = fields.Datetime(string='Order Date', required=True, readonly=False, index=True, copy=False, default=fields.Datetime.now, help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.")
    shipper_id = fields.Char("Shipper ID", size=64)
    payment_amount = fields.Integer("Payment")
    payment_journal_id = fields.Many2one("account.journal")
    _sql_constraints = [('name_unique', 'unique(name)','name must be unique!')]

    @api.onchange('shipper_id')
    def onchange_shipper_id(self):
        if self.shipper_id:
            self.partner_id = self.env['res.partner'].search([("shipper_id","=",self.shipper_id)])

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.shipper_id:
            so_partner = self.env['res.partner'].search([("shipper_id","=",self.shipper_id)])
            invoice_vals['partner_id'] = so_partner.id
            invoice_vals['partner_shipping_id'] = so_partner.id
            invoice_vals['invoice_date'] = self.date_order
            invoice_vals['ref'] = self.name
        return invoice_vals
    
    def _prepare_confirmation_values(self):
        #bypass order date automation
        return {
            'state': 'sale',
        }

    @api.model
    def create(self,vals):
        if vals['shipper_id']:
            created_partner = self.env['cbiz.api.cargoapi'].cargo_sync_shipper(vals['shipper_id'])
            vals['partner_id'] = created_partner.id
            vals['partner_invoice_id'] = created_partner.id
            vals['partner_shipping_id'] = created_partner.id
        create_response = super(SaleOrder,self).create(vals)
        return create_response

    def action_confirm(self):
        action_confirm = super(SaleOrder,self).action_confirm()
        for order in self:
            if self.shipper_id and order.picking_ids: 
                for picking in self.picking_ids:
                    picking.action_assign()
                    picking.action_confirm()
                    for mv in picking.move_ids_without_package:
                        mv.quantity_done = mv.product_uom_qty
                    picking.button_validate()

            if self.shipper_id and not order.invoice_ids:
                order._create_invoices()  

            if self.shipper_id and order.invoice_ids:
                for invoice in order.invoice_ids:
                    invoice.action_post()
                if self.payment_amount:
                    payment = invoice.env['account.payment.register'].with_context({
                        "active_model":"account.move",
                        "active_ids":invoice.id
                    }).create([{
                        "payment_date": self.date_order,
                        "amount": self.payment_amount,
                        "journal_id": self.payment_journal_id.id,
                        "payment_method_id": 1,
                        "company_id": self.company_id.id
                    }])
                    payment.action_create_payments()
        return action_confirm