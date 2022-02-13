import pytz
from datetime import datetime,timedelta
from functools import partial

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero, float_round
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
from odoo.osv.expression import AND
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp

class PaymentReport(models.AbstractModel):
    _name = 'report.imerex_pos_payment_report.imerex_pos_payment_report_doc'
    _description = 'POS payment report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        date_start = False
        date_stop = False
        if data['date_start']:
            date_start = fields.Datetime.from_string(data['date_start'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_end']:
            date_stop = fields.Datetime.from_string(data['date_end'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)

        pos_payment_env = self.env["pos.payment"]
        pos_payment_method_env = self.env["pos.payment.method"]

        pos_payment_method_domain = []
        if data.get('company_ids', False):
            pos_payment_method_domain.append(('company_id','in',data.get('company_ids', False)))
        pos_payment_method_search = pos_payment_method_env.sudo().search(pos_payment_method_domain)
        column_name_list = ["Invoice", "Customer"]
        column_pos_payment_value_list = []
        
        for pos_payment_method in pos_payment_method_search:
            if pos_payment_method.name not in column_name_list:
                column_name_list.append(pos_payment_method.name)
            if pos_payment_method.name not in column_pos_payment_value_list:
                column_pos_payment_value_list.append(pos_payment_method.name)

        column_name_list.append("Total")
        column_pos_payment_value_list.append("Total")

        currency = False
        grand_journal_dict = {}
        total_payment_refund = 0.0
        picking_ids_dict = {}
        pos_terminal_dict = {}
        if data.get("config_ids", False):
            for pos_terminal in data.get("config_ids"):
                session_ids = self.env['pos.session'].sudo().search(
                    [('config_id', '=', pos_terminal),('start_at','>=',fields.Datetime.to_string(date_start))]
                    )
                session_dict = {}
                session_journal_dict = {}
                payment_refund = 0.0
                pos_config = self.env['pos.config'].browse(pos_terminal)
                picking_ids_dict.update({
                    pos_config.name: {
                        'warehouse': pos_config.picking_type_id.warehouse_id.id,
                        'sessions': session_ids.picking_ids
                    }
                })
                for session_id in session_ids:
                    domain = [
                        ("payment_date", ">=", fields.Datetime.to_string(date_start)),
                        ("payment_date", "<=", fields.Datetime.to_string(date_stop)),
                    ]
                    if data.get("state", False):
                        state = data.get("state")
                        if state == 'all':
                            domain.append(
                                ('pos_order_id.state', 'not in', ['cancel']))
                        elif state == 'open':
                            domain.append(
                                ('pos_order_id.state', 'in', ['draft']))
                        elif state == 'paid':
                            domain.append(
                                ('pos_order_id.state', 'in', ['paid']))
                    if data.get('company_ids', False):
                        domain.append(
                            ("company_id", "in", data.get('company_ids', False)))
                    domain.append(
                        ("pos_order_id.session_id", "=", session_id.id))
                    pos_payments = pos_payment_env.sudo().search(domain)
                    invoice_pay_dict = {}
                    if pos_payments and pos_payment_method_search:
                        for each_pos_payment_method in pos_payment_method_search:
                            # journal wise payment first we total all bank, cash etc etc.
                            for each_pos_payment in pos_payments.filtered(lambda x: x.payment_method_id.id == each_pos_payment_method.id):
                                if data.get('filter_invoice_data') and data.get('filter_invoice_data') == 'all':
                                    if each_pos_payment.pos_order_id.account_move:
                                        for invoice in each_pos_payment.pos_order_id.account_move:
                                            if not currency:
                                                currency = invoice.currency_id
                                            if invoice.move_type == "out_invoice":
                                                if invoice_pay_dict.get(invoice.name, False):
                                                    pay_dict = invoice_pay_dict.get(
                                                        invoice.name)
                                                    total = pay_dict.get("Total")
                                                    if pay_dict.get(each_pos_payment_method.name, False):
                                                        amount = pay_dict.get(
                                                            each_pos_payment_method.name)
                                                        total += each_pos_payment.amount
                                                        amount += each_pos_payment.amount
                                                        pay_dict.update(
                                                            {each_pos_payment_method.name: amount, "Total": total})
                                                    else:
                                                        total += each_pos_payment.amount
                                                        pay_dict.update(
                                                            {each_pos_payment_method.name: each_pos_payment.amount, "Total": total})
        
                                                    invoice_pay_dict.update(
                                                        {invoice.name: pay_dict})
                                                else:
                                                    invoice_pay_dict.update({invoice.name: {each_pos_payment_method.name: each_pos_payment.amount, "Total": each_pos_payment.amount, "Invoice": invoice.name,
                                                                                        "Customer": invoice.partner_id.name, "Invoice Date": invoice.invoice_date, "User": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;'}})
                                            if invoice.move_type == "out_refund":
                                                payment_refund += each_pos_payment.amount
                                                if invoice_pay_dict.get(invoice.name, False):
                                                    pay_dict = invoice_pay_dict.get(
                                                        invoice.name)
                                                    total = pay_dict.get("Total")
                                                    if pay_dict.get(each_pos_payment_method.name, False):
                                                        amount = pay_dict.get(
                                                            each_pos_payment_method.name)
                                                        total -= each_pos_payment.amount
                                                        amount -= each_pos_payment.amount
                                                        pay_dict.update(
                                                            {each_pos_payment_method.name: amount, "Total": total})
                                                    else:
                                                        total -= each_pos_payment.amount
                                                        pay_dict.update(
                                                            {each_pos_payment_method.name: -1 * (each_pos_payment.amount), "Total": total})
        
                                                    invoice_pay_dict.update(
                                                        {invoice.name: pay_dict})
        
                                                else:
                                                    invoice_pay_dict.update({invoice.name: {each_pos_payment_method.name: -1 * (each_pos_payment.amount), "Total": -1 * (each_pos_payment.amount), "Invoice": invoice.name,
                                                                                        "Customer": invoice.partner_id.name, "Invoice Date": invoice.invoice_date, "User": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;color:red'}})
                                    else:
                                        if not currency:
                                            currency = each_pos_payment.currency_id
                                        if invoice_pay_dict.get(each_pos_payment.pos_order_id.name, False):
                                            pay_dict = invoice_pay_dict.get(
                                                each_pos_payment.pos_order_id.name)
                                            total = pay_dict.get("Total")
                                            if pay_dict.get(each_pos_payment_method.name, False):
                                                amount = pay_dict.get(
                                                    each_pos_payment_method.name)
                                                total += each_pos_payment.amount
                                                amount += each_pos_payment.amount
                                                pay_dict.update(
                                                    {each_pos_payment_method.name: amount, "Total": total})
                                            else:
                                                total += each_pos_payment.amount
                                                pay_dict.update(
                                                    {each_pos_payment_method.name: each_pos_payment.amount, "Total": total})
        
                                            invoice_pay_dict.update(
                                                {each_pos_payment.pos_order_id.name: pay_dict})
                                        else:
                                            invoice_pay_dict.update({each_pos_payment.pos_order_id.name: {each_pos_payment_method.name: each_pos_payment.amount, "Total": each_pos_payment.amount, "Invoice": each_pos_payment.pos_order_id.name,
                                                                                "Customer": each_pos_payment.pos_order_id.partner_id.name, "Invoice Date": each_pos_payment.payment_date.date(), "User": each_pos_payment.pos_order_id.user_id.name if each_pos_payment.pos_order_id.user_id else "", "style": 'border: 1px solid black;'}})
                                elif data.get('filter_invoice_data') and data.get('filter_invoice_data') == 'with_invoice':
                                    if each_pos_payment.pos_order_id.account_move:
                                        for invoice in each_pos_payment.pos_order_id.account_move:
                                            if not currency:
                                                currency = invoice.currency_id
                                            if invoice.move_type == "out_invoice":
                                                if invoice_pay_dict.get(invoice.name, False):
                                                    pay_dict = invoice_pay_dict.get(
                                                        invoice.name)
                                                    total = pay_dict.get("Total")
                                                    if pay_dict.get(each_pos_payment_method.name, False):
                                                        amount = pay_dict.get(
                                                            each_pos_payment_method.name)
                                                        total += each_pos_payment.amount
                                                        amount += each_pos_payment.amount
                                                        pay_dict.update(
                                                            {each_pos_payment_method.name: amount, "Total": total})
                                                    else:
                                                        total += each_pos_payment.amount
                                                        pay_dict.update(
                                                            {each_pos_payment_method.name: each_pos_payment.amount, "Total": total})
        
                                                    invoice_pay_dict.update(
                                                        {invoice.name: pay_dict})
                                                else:
                                                    invoice_pay_dict.update({invoice.name: {each_pos_payment_method.name: each_pos_payment.amount, "Total": each_pos_payment.amount, "Invoice": invoice.name,
                                                                                        "Customer": invoice.partner_id.name, "Invoice Date": invoice.invoice_date, "User": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;'}})
                                            if invoice.move_type == "out_refund":
                                                payment_refund += each_pos_payment.amount
                                                if invoice_pay_dict.get(invoice.name, False):
                                                    pay_dict = invoice_pay_dict.get(
                                                        invoice.name)
                                                    total = pay_dict.get("Total")
                                                    if pay_dict.get(each_pos_payment_method.name, False):
                                                        amount = pay_dict.get(
                                                            each_pos_payment_method.name)
                                                        total -= each_pos_payment.amount
                                                        amount -= each_pos_payment.amount
                                                        pay_dict.update(
                                                            {each_pos_payment_method.name: amount, "Total": total})
                                                    else:
                                                        total -= each_pos_payment.amount
                                                        pay_dict.update(
                                                            {each_pos_payment_method.name: -1 * (each_pos_payment.amount), "Total": total})
        
                                                    invoice_pay_dict.update(
                                                        {invoice.name: pay_dict})
        
                                                else:
                                                    invoice_pay_dict.update({invoice.name: {each_pos_payment_method.name: -1 * (each_pos_payment.amount), "Total": -1 * (each_pos_payment.amount), "Invoice": invoice.name,
                                                                                        "Customer": invoice.partner_id.name, "Invoice Date": invoice.invoice_date, "User": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;color:red'}})
                                elif data.get('filter_invoice_data') and data.get('filter_invoice_data') == 'wo_invoice':
                                    if not currency:
                                        currency = each_pos_payment.currency_id
                                    if invoice_pay_dict.get(each_pos_payment.pos_order_id.name, False):
                                        pay_dict = invoice_pay_dict.get(
                                            each_pos_payment.pos_order_id.name)
                                        total = pay_dict.get("Total")
                                        if pay_dict.get(each_pos_payment_method.name, False):
                                            amount = pay_dict.get(
                                                each_pos_payment_method.name)
                                            total += each_pos_payment.amount
                                            amount += each_pos_payment.amount
                                            pay_dict.update(
                                                {each_pos_payment_method.name: amount, "Total": total})
                                        else:
                                            total += each_pos_payment.amount
                                            pay_dict.update(
                                                {each_pos_payment_method.name: each_pos_payment.amount, "Total": total})

                                        invoice_pay_dict.update(
                                            {each_pos_payment.pos_order_id.name: pay_dict})
                                    else:
                                        invoice_pay_dict.update({each_pos_payment.pos_order_id.name: {each_pos_payment_method.name: each_pos_payment.amount, "Total": each_pos_payment.amount, "Invoice": each_pos_payment.pos_order_id.name,
                                                                            "Customer": each_pos_payment.pos_order_id.partner_id.name, "Invoice Date": each_pos_payment.payment_date.date(), "User": each_pos_payment.pos_order_id.user_id.name if each_pos_payment.pos_order_id.user_id else "", "style": 'border: 1px solid black;'}})
                    # all final list and [{},{},{}] format
                    # here we get the below total.
                    # total each_pos_payment_method amount is a grand total and format is : {} just a dictionary
                    final_list = []
                    total_payment_amount = {}
                    for key, value in invoice_pay_dict.items():
                        final_list.append(value)
                        for col_name in column_pos_payment_value_list:
                            if total_payment_amount.get(col_name, False):
                                total = total_payment_amount.get(col_name)
                                total += value.get(col_name, 0.0)

                                total_payment_amount.update({col_name: total})
                            else:
                                total_payment_amount.update(
                                    {col_name: value.get(col_name, 0.0)})

                    total_payment_amount.update({'Customer': 'Payment Total'})
                    # finally make user wise dic here.
                    search_session_id = self.env['pos.session'].sudo().search([
                        ('id', '=', session_id.id)
                    ], limit=1)
                    if search_session_id:
                        session_dict.update({
                            search_session_id.name: {'pay': final_list,
                                            'grand_total': total_payment_amount,
                                            'user': search_session_id.user_id.name
                                            }
                        })

                    for col_name in column_pos_payment_value_list:
                        payment_total = 0.0
                        payment_total = total_payment_amount.get(col_name, 0.0)
                        payment_total += session_journal_dict.get(col_name, 0.0)
                        session_journal_dict.update({col_name: payment_total})

                payment_refund = payment_refund * -1
                total_payment_refund += payment_refund
                session_journal_dict.update({'Refund': payment_refund})

                grand_final_list = []
                grand_payment_amount = {}
                for key, value in session_dict.items():
                    grand_final_list.append(value['grand_total'])
                    for col_name in column_pos_payment_value_list:
                        if grand_payment_amount.get(col_name, False):
                            total = grand_payment_amount.get(col_name)
                            total += value['grand_total'].get(col_name, 0.0)

                            grand_payment_amount.update({col_name: total})
                        else:
                            grand_payment_amount.update(
                                {col_name: value['grand_total'].get(col_name, 0.0)})

                grand_payment_amount.update({'Customer': 'Payment Total'})
                search_pos_terminal_id = self.env['pos.config'].sudo().search([
                        ('id', '=', pos_terminal)], limit=1)
                
                if search_pos_terminal_id:
                    pos_terminal_dict.update({
                        search_pos_terminal_id.name: session_dict
                        })

                for col_name in column_pos_payment_value_list:
                    grand_payment_total = 0.0
                    grand_payment_total = grand_payment_amount.get(col_name, 0.0)
                    grand_payment_total += grand_journal_dict.get(col_name, 0.0)
                    grand_journal_dict.update({col_name: grand_payment_total})

            total_payment_refund = total_payment_refund * -1
            grand_journal_dict.update({'Refund': total_payment_refund})
        
        data.update({
            'date_start': data['date_start'],
            'date_end': data['date_end'],
            'columns': column_name_list,
            'pos_terminal_dict': pos_terminal_dict,
            'currency': currency,
            'grand_journal_dict': grand_journal_dict,
        })

        configs = self.env['pos.config'].browse(data['config_ids'])

        picking_ids_dict
        pos_stock_movement = {}
        for key,values in picking_ids_dict.items():
            stock_movement = []
            product_beginning_qty = {}
            product_ending_qty={}
            if values['sessions']:
                stock_move = self.env['stock.move'].search([('picking_id', 'in', values['sessions'].ids)])
                stock_move_line = self.env['stock.move.line'].search(
                    [('picking_id', 'in', values['sessions'].ids), ('move_id', 'in', stock_move.ids)])
                initial_date = self.env['stock.move.line'].browse(min(stock_move_line.ids)).date
                end_date = self.env['stock.move.line'].browse(max(stock_move_line.ids)).date
                all_pos_products = self.env['product.product'].search([('available_in_pos','=',True)]).ids
                for product in all_pos_products:
                    product_details = self.env['product.product'].browse(product)
                    product_beginning_qty.update({
                        product_details.id : {
                            'name': product_details.name,
                            'begin_qty': product_details.with_context({
                                'to_date': initial_date + timedelta(seconds=-1),
                                'warehouse': values['warehouse']}).qty_available
                        }
                    })
                for product in all_pos_products:
                    product_details = self.env['product.product'].browse(product)
                    product_ending_qty.update({
                        product_details.id : {
                            'name': product_details.name,
                            'end_qty': product_details.with_context({
                                'to_date': end_date + timedelta(seconds=1),
                                'warehouse': values['warehouse']}).qty_available
                        }
                    })

                if stock_move_line:
                    for record in stock_move_line:
                        stock_movement.append({
                            'name': record.product_id.name,
                            'move_qty': round(record.product_id.qty_available - record.product_id.outgoing_qty, 2),
                            'outgoing_qty': round(record.qty_done, 2),
                            'qty_available': round(record.product_id.qty_available, 2),
                            'reserved_qty': round(record.product_uom_qty, 2)})

                pos_stock_movement.update({
                    key : stock_movement
                })       
        data.update({
            'pos_stock_movement': pos_stock_movement
        })
        data.update(self.get_sale_details(data['date_start'], data['date_end'], configs.ids))
        return data


    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        """ Serialise the orders of the requested time period, configs and sessions.

        :param date_start: The dateTime to start, default today 00:00:00.
        :type date_start: str.
        :param date_stop: The dateTime to stop, default date_start + 23:59:59.
        :type date_stop: str.
        :param config_ids: Pos Config id's to include.
        :type config_ids: list of numbers.
        :param session_ids: Pos Config id's to include.
        :type session_ids: list of numbers.

        :returns: dict -- Serialised sales.
        """
        domain = [('state', 'in', ['paid','invoiced','done'])]

        if (session_ids):
            domain = AND([domain, [('session_id', 'in', session_ids)]])
        else:
            if date_start:
                date_start = fields.Datetime.from_string(date_start)
            else:
                # start by default today 00:00:00
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
                date_start = today.astimezone(pytz.timezone('UTC'))

            if date_stop:
                date_stop = fields.Datetime.from_string(date_stop)
                # avoid a date_stop smaller than date_start
                if (date_stop < date_start):
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                # stop by default today 23:59:59
                date_stop = date_start + timedelta(days=1, seconds=-1)

            domain = AND([domain,
                [('date_order', '>=', fields.Datetime.to_string(date_start)),
                ('date_order', '<=', fields.Datetime.to_string(date_stop))]
            ])

            if config_ids:
                domain = AND([domain, [('config_id', 'in', config_ids)]])

        orders = self.env['pos.order'].search(domain)

        user_currency = self.env.company.currency_id

        total = 0.0
        products_sold = {}
        taxes = {}
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id._convert(
                    order.amount_total, user_currency, order.company_id, order.date_order or fields.Date.today())
            else:
                total += order.amount_total
            currency = order.session_id.currency_id

            for line in order.lines:
                key = (line.product_id, line.price_unit, line.discount)
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(line.price_unit * (1-(line.discount or 0.0)/100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount':0.0, 'base_amount':0.0, 'grand_amount':0.0})
                        taxes[tax['id']]['tax_amount'] += tax['amount']
                        taxes[tax['id']]['base_amount'] += tax['base']
                        taxes[tax['id']]['grand_amount'] += tax['base'] + tax['amount']
                else:
                    taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount':0.0, 'base_amount':0.0, 'grand_amount':0.0})
                    taxes[0]['base_amount'] += line.price_subtotal_incl
                    taxes[0]['grand_amount'] += line.price_subtotal_incl
        
        payment_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
        if payment_ids:
            self.env.cr.execute("""
                SELECT method.name, sum(amount) total
                FROM pos_payment AS payment,
                     pos_payment_method AS method
                WHERE payment.payment_method_id = method.id
                    AND payment.id IN %s
                GROUP BY method.name
            """, (tuple(payment_ids),))
            pos_payments = self.env.cr.dictfetchall()
        else:
            pos_payments = []

        return {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'pos_payments': pos_payments,
            'company_name': self.env.company.name,
            'taxes': list(taxes.values()),
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'discount': discount,
                'uom': product.uom_id.name
            } for (product, price_unit, discount), qty in products_sold.items()], key=lambda l: l['product_name'])
        }
class ProductProduct(models.Model):
    _inherit = "product.product"
    
    reserved_qty = fields.Float(compute="_compute_quantity",string="Reserved Quantity",default=0)
    available_qty = fields.Float(compute="_compute_quantity",string="Available Quantity",default=0)
    
    def _compute_quantity(self):
        stock_picking_obj = self.env['stock.picking']
        total_reserved = 0.0
        for pro in self:
            stock_move_ids = self.env['stock.move'].search([('product_id','=',pro.id),('state','not in',['done','cancel'])])
            for move in stock_move_ids:
                if not move.picking_id.picking_type_id.code == 'incoming' :
                    total_reserved = total_reserved + move.reserved_availability
            pro.reserved_qty = total_reserved
            pro.available_qty = pro.qty_available - pro.reserved_qty
            
        return

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    reserved_qty = fields.Float(compute="_compute_quantity",string="Reserved Quantity",default=0)
    available_qty = fields.Float(compute="_compute_quantity",string="Available Quantity",default=0)
    
    def _compute_quantity(self):
        stock_picking_obj = self.env['stock.picking']
        total_reserved = 0.0
        for pro in self:
            for line in pro.product_variant_ids :
                
                stock_move_ids = self.env['stock.move'].search([('product_id','=',line.id),('state','not in',['done','cancel'])])
                for move in stock_move_ids:
                    if not move.picking_id.picking_type_id.code == 'incoming' :
                        total_reserved = total_reserved + move.reserved_availability

                
            pro.reserved_qty = total_reserved
            
            pro.available_qty = pro.qty_available - pro.reserved_qty
            
        return