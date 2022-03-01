from odoo import api, fields, models
from odoo.tools.misc import unique

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
        invoice_vals['invoice_date'] = self.date_order
        invoice_vals['ref'] = self.name
        return invoice_vals
    
    def _prepare_confirmation_values(self):
        #bypass order date automation
        return {
            'state': 'sale',
        }

    def action_confirm(self):
        action_confirm = super(SaleOrder,self).action_confirm()
        for order in self:
            if self.payment_journal_id and order.picking_ids: 
                for picking in self.picking_ids:
                    picking.action_assign()
                    picking.action_confirm()
                    for mv in picking.move_ids_without_package:
                        mv.quantity_done = mv.product_uom_qty
                    # picking.button_validate()

            if self.payment_journal_id and not order.invoice_ids:
                order._create_invoices()
                for invoice in order.invoice_ids:
                    invoice.action_post()

            if self.payment_journal_id and order.invoice_ids and self.payment_amount:
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