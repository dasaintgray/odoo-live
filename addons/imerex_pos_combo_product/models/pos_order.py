# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, _
from functools import partial


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    parent_id = fields.Many2one('product.product', string="Products", copy=False, help="Manage Main Product")
    sub_product_line = fields.Boolean('combo product', copy=False, help="is sub product then true")
    is_combo_line = fields.Boolean('Combo line', copy=False, help="Check Combo Product or not")
    select_combo_ids = fields.Many2many('product.combo', string='Selected Combo Product', copy=False)
    final_combo_price = fields.Float('Combo Price', help="Combo price with include all products price")


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _order_fields(self, ui_order):
        """
            This method is use for add combo product in pos order lines with bifurcate of 
            include price with main product or not.
        """
        result = super(PosOrder, self)._order_fields(ui_order)
        partner_id = self.env['res.partner'].browse(ui_order.get('partner_id'))
        price_list_id = self.env['product.pricelist'].search([('id', '=', ui_order.get('pricelist_id'))])
        product_obj = self.env['product.product']
        process_line = partial(self.env['pos.order.line']._order_line_fields, session_id=ui_order['pos_session_id'])
        product_line = [process_line(l) for l in ui_order['lines']]
        combo_obj = self.env['product.combo']
        account_tax_obj = self.env['account.tax']
        combo_line = []
        for line in product_line:
            if line[2].get('is_combo_line'):
                tax_id = account_tax_obj.browse(line[2]['tax_ids'][0][2])
                product_id = product_obj.browse(line[2]['product_id'])
                product_context = dict(self.env.context, partner_id=partner_id.id, date=ui_order['creation_date'], uom=product_id.uom_id.id)
                main_product_new_price, rule_id = price_list_id.with_context(product_context).get_product_price_rule(product_id, line[2]['qty'] or 1.0, partner_id)
                main_product_price = main_product_new_price * (1 - (line[2]['discount'] or 0.0) / 100.0)
                main_product_taxes = tax_id.compute_all(main_product_price, price_list_id.currency_id, line[2]['qty'], product=product_id, partner=partner_id)
                line[2].update({'price_subtotal': main_product_taxes['total_excluded'],
                    'price_subtotal_incl': main_product_taxes['total_included'],
                    'price_unit': main_product_price,
                    })
        for line in ui_order.get('lines'):
            if line[2].get('is_combo_line'):
                selected_product_list = line[2].get('req_product_ids') + line[2].get('unreq_product_ids')
                line[2].update({'req_product': line[2].get('req_product_ids'), 'unreq_product': line[2].get('unreq_product_ids'), 'final_combo_price': line[2]['price_unit'], \
                    'select_combo_ids': [(6, 0, [int(l) for l in line[2]['select_combo_id']] if line[2].get('select_combo_id') else '')]
                    })
                for combo_product_id in line[2]['select_combo_id']:
                    combo_id = combo_obj.search([('id', '=', combo_product_id)])
                    if not combo_id.is_include_in_main_product_price:
                        for excl_product_id in combo_id.product_ids:
                            if excl_product_id.id in selected_product_list:
                                product_context = dict(self.env.context, partner_id=partner_id.id, date=ui_order['creation_date'], uom=excl_product_id.uom_id.id)
                                if combo_id.combo_pricing >= 0:
                                    new_price = combo_id.combo_pricing
                                else:
                                    new_price, rule_id = price_list_id.with_context(product_context).get_product_price_rule(excl_product_id, line[2]['qty'] or 1.0, partner_id)
                                price = new_price * (1 - (line[2]['discount'] or 0.0) / 100.0)
                                taxes = tax_id.compute_all(price, price_list_id.currency_id, line[2]['qty'], product=excl_product_id, partner=partner_id)
                                combo_line.append((0, 0, {'product_id': excl_product_id.id,
                                    'price_subtotal': taxes['total_excluded'],
                                    'sub_product_line': True,
                                    'parent_id': line[2]['product_id'],
                                    'tax_ids': line[2]['tax_ids'],
                                    'price_subtotal_incl': taxes['total_included'],
                                    'discount': line[2]['discount'],
                                    'id': excl_product_id.id,
                                    'pack_lot_ids': line[2]['pack_lot_ids'],
                                    'qty': line[2]['qty'],
                                    'price_unit': price,
                                    'full_product_name': line[2]['combo_product_attribute_values'][0][str(excl_product_id.id)]['full_name_product'] or '',
                                    'name': line[2]['name'] if line[2].get('name') else excl_product_id.name}))
                                selected_product_list.remove(excl_product_id.id)
                    else:
                        for incl_product_id in combo_id.product_ids:
                            if incl_product_id.id in line[2].get('req_product_ids'):
                                combo_line.append((0, 0, {'product_id': incl_product_id.id,
                                    'price_subtotal': 0.00,
                                    'sub_product_line': True,
                                    'parent_id': line[2]['product_id'],
                                    'tax_ids': line[2]['tax_ids'],
                                    'price_subtotal_incl': 0.00,
                                    'discount': line[2]['discount'],
                                    'id': incl_product_id.id,
                                    'pack_lot_ids': line[2]['pack_lot_ids'],
                                    'qty': line[2]['qty'],
                                    'price_unit': 0.00,
                                    'full_product_name': line[2]['combo_product_attribute_values'][0][str(incl_product_id.id)]['full_name_product'] or '',
                                    'name': line[2]['name'] if line[2].get('name') else incl_product_id.name}))
                                selected_product_list.remove(incl_product_id.id)
        if combo_line:
            product_line += combo_line
        result.update({'lines': [process_line(l) for l in product_line] if product_line else False})
        return result

    def _prepare_invoice_line(self, order_line):
        result = super(PosOrder, self)._prepare_invoice_line(order_line)
        result.update({
            'parent_id': order_line.parent_id.id,
            'sub_product_line': order_line.sub_product_line,
            'pos_line_name': order_line.name,
        })
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: