# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

import pytz
from datetime import datetime,timedelta
import logging
from functools import partial

import psycopg2
import re

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero, float_round
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
from odoo.osv.expression import AND
import base64


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
        account_payment_obj = self.env["pos.payment"]
        account_journal_obj = self.env["pos.payment.method"]
        journal_domain = []
        if data.get('company_ids', False):
            journal_domain.append(('company_id','in',data.get('company_ids', False)))
        search_journals = account_journal_obj.sudo().search(journal_domain)
        final_col_list = ["Invoice", "Customer"]
        final_total_col_list = []
        for journal in search_journals:
            if journal.name not in final_col_list:
                final_col_list.append(journal.name)
            if journal.name not in final_total_col_list:
                final_total_col_list.append(journal.name)

        final_col_list.append("Total")
        final_total_col_list.append("Total")

        currency = False
        grand_journal_dic = {}
        j_refund = 0.0

        user_data_dic = {}
        if data.get("user_ids", False):

            for user_id in data.get("user_ids"):

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
                domain.append(
                    ("pos_order_id.user_id", "=", user_id))
                if data.get('company_ids', False):
                    domain.append(
                        ("company_id", "in", data.get('company_ids', False)))
                if data.get('config_ids', False):
                    session_ids = self.env['pos.session'].sudo().search(
                        [('config_id', 'in', data.get('config_ids', False))])
                    domain.append(
                        ("pos_order_id.session_id", "in", session_ids.ids))
                payments = account_payment_obj.sudo().search(domain)
                invoice_pay_dic = {}
                if payments and search_journals:
                    for journal in search_journals:
                        # journal wise payment first we total all bank, cash etc etc.
                        for journal_wise_payment in payments.filtered(lambda x: x.payment_method_id.id == journal.id):
                            if data.get('filter_invoice_data') and data.get('filter_invoice_data') == 'all':
                                if journal_wise_payment.pos_order_id.account_move:
                                    for invoice in journal_wise_payment.pos_order_id.account_move:
                                        if not currency:
                                            currency = invoice.currency_id
                                        if invoice.move_type == "out_invoice":
                                            if invoice_pay_dic.get(invoice.name, False):
                                                pay_dic = invoice_pay_dic.get(
                                                    invoice.name)
                                                total = pay_dic.get("Total")
                                                if pay_dic.get(journal.name, False):
                                                    amount = pay_dic.get(
                                                        journal.name)
                                                    total += journal_wise_payment.amount
                                                    amount += journal_wise_payment.amount
                                                    pay_dic.update(
                                                        {journal.name: amount, "Total": total})
                                                else:
                                                    total += journal_wise_payment.amount
                                                    pay_dic.update(
                                                        {journal.name: journal_wise_payment.amount, "Total": total})
    
                                                invoice_pay_dic.update(
                                                    {invoice.name: pay_dic})
                                            else:
                                                invoice_pay_dic.update({invoice.name: {journal.name: journal_wise_payment.amount, "Total": journal_wise_payment.amount, "Invoice": invoice.name,
                                                                                       "Customer": invoice.partner_id.name, "Invoice Date": invoice.invoice_date, "User": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;'}})
                                        if invoice.move_type == "out_refund":
                                            j_refund += journal_wise_payment.amount
                                            if invoice_pay_dic.get(invoice.name, False):
                                                pay_dic = invoice_pay_dic.get(
                                                    invoice.name)
                                                total = pay_dic.get("Total")
                                                if pay_dic.get(journal.name, False):
                                                    amount = pay_dic.get(
                                                        journal.name)
                                                    total -= journal_wise_payment.amount
                                                    amount -= journal_wise_payment.amount
                                                    pay_dic.update(
                                                        {journal.name: amount, "Total": total})
                                                else:
                                                    total -= journal_wise_payment.amount
                                                    pay_dic.update(
                                                        {journal.name: -1 * (journal_wise_payment.amount), "Total": total})
    
                                                invoice_pay_dic.update(
                                                    {invoice.name: pay_dic})
    
                                            else:
                                                invoice_pay_dic.update({invoice.name: {journal.name: -1 * (journal_wise_payment.amount), "Total": -1 * (journal_wise_payment.amount), "Invoice": invoice.name,
                                                                                       "Customer": invoice.partner_id.name, "Invoice Date": invoice.invoice_date, "User": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;color:red'}})
                                else:
                                    if not currency:
                                        currency = journal_wise_payment.currency_id
                                    if invoice_pay_dic.get(journal_wise_payment.pos_order_id.name, False):
                                        pay_dic = invoice_pay_dic.get(
                                            journal_wise_payment.pos_order_id.name)
                                        total = pay_dic.get("Total")
                                        if pay_dic.get(journal.name, False):
                                            amount = pay_dic.get(
                                                journal.name)
                                            total += journal_wise_payment.amount
                                            amount += journal_wise_payment.amount
                                            pay_dic.update(
                                                {journal.name: amount, "Total": total})
                                        else:
                                            total += journal_wise_payment.amount
                                            pay_dic.update(
                                                {journal.name: journal_wise_payment.amount, "Total": total})
     
                                        invoice_pay_dic.update(
                                            {journal_wise_payment.pos_order_id.name: pay_dic})
                                    else:
                                        invoice_pay_dic.update({journal_wise_payment.pos_order_id.name: {journal.name: journal_wise_payment.amount, "Total": journal_wise_payment.amount, "Invoice": journal_wise_payment.pos_order_id.name,
                                                                               "Customer": journal_wise_payment.pos_order_id.partner_id.name, "Invoice Date": journal_wise_payment.payment_date.date(), "User": journal_wise_payment.pos_order_id.user_id.name if journal_wise_payment.pos_order_id.user_id else "", "style": 'border: 1px solid black;'}})
                            elif data.get('filter_invoice_data') and data.get('filter_invoice_data') == 'with_invoice':
                                if journal_wise_payment.pos_order_id.account_move:
                                    for invoice in journal_wise_payment.pos_order_id.account_move:
                                        if not currency:
                                            currency = invoice.currency_id
                                        if invoice.move_type == "out_invoice":
                                            if invoice_pay_dic.get(invoice.name, False):
                                                pay_dic = invoice_pay_dic.get(
                                                    invoice.name)
                                                total = pay_dic.get("Total")
                                                if pay_dic.get(journal.name, False):
                                                    amount = pay_dic.get(
                                                        journal.name)
                                                    total += journal_wise_payment.amount
                                                    amount += journal_wise_payment.amount
                                                    pay_dic.update(
                                                        {journal.name: amount, "Total": total})
                                                else:
                                                    total += journal_wise_payment.amount
                                                    pay_dic.update(
                                                        {journal.name: journal_wise_payment.amount, "Total": total})
    
                                                invoice_pay_dic.update(
                                                    {invoice.name: pay_dic})
                                            else:
                                                invoice_pay_dic.update({invoice.name: {journal.name: journal_wise_payment.amount, "Total": journal_wise_payment.amount, "Invoice": invoice.name,
                                                                                       "Customer": invoice.partner_id.name, "Invoice Date": invoice.invoice_date, "User": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;'}})
                                        if invoice.move_type == "out_refund":
                                            j_refund += journal_wise_payment.amount
                                            if invoice_pay_dic.get(invoice.name, False):
                                                pay_dic = invoice_pay_dic.get(
                                                    invoice.name)
                                                total = pay_dic.get("Total")
                                                if pay_dic.get(journal.name, False):
                                                    amount = pay_dic.get(
                                                        journal.name)
                                                    total -= journal_wise_payment.amount
                                                    amount -= journal_wise_payment.amount
                                                    pay_dic.update(
                                                        {journal.name: amount, "Total": total})
                                                else:
                                                    total -= journal_wise_payment.amount
                                                    pay_dic.update(
                                                        {journal.name: -1 * (journal_wise_payment.amount), "Total": total})
    
                                                invoice_pay_dic.update(
                                                    {invoice.name: pay_dic})
    
                                            else:
                                                invoice_pay_dic.update({invoice.name: {journal.name: -1 * (journal_wise_payment.amount), "Total": -1 * (journal_wise_payment.amount), "Invoice": invoice.name,
                                                                                       "Customer": invoice.partner_id.name, "Invoice Date": invoice.invoice_date, "User": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;color:red'}})
                            elif data.get('filter_invoice_data') and data.get('filter_invoice_data') == 'wo_invoice':
                                if not currency:
                                    currency = journal_wise_payment.currency_id
                                if invoice_pay_dic.get(journal_wise_payment.pos_order_id.name, False):
                                    pay_dic = invoice_pay_dic.get(
                                        journal_wise_payment.pos_order_id.name)
                                    total = pay_dic.get("Total")
                                    if pay_dic.get(journal.name, False):
                                        amount = pay_dic.get(
                                            journal.name)
                                        total += journal_wise_payment.amount
                                        amount += journal_wise_payment.amount
                                        pay_dic.update(
                                            {journal.name: amount, "Total": total})
                                    else:
                                        total += journal_wise_payment.amount
                                        pay_dic.update(
                                            {journal.name: journal_wise_payment.amount, "Total": total})

                                    invoice_pay_dic.update(
                                        {journal_wise_payment.pos_order_id.name: pay_dic})
                                else:
                                    invoice_pay_dic.update({journal_wise_payment.pos_order_id.name: {journal.name: journal_wise_payment.amount, "Total": journal_wise_payment.amount, "Invoice": journal_wise_payment.pos_order_id.name,
                                                                           "Customer": journal_wise_payment.pos_order_id.partner_id.name, "Invoice Date": journal_wise_payment.payment_date.date(), "User": journal_wise_payment.pos_order_id.user_id.name if journal_wise_payment.pos_order_id.user_id else "", "style": 'border: 1px solid black;'}})
                # all final list and [{},{},{}] format
                # here we get the below total.
                # total journal amount is a grand total and format is : {} just a dictionary
                final_list = []
                total_journal_amount = {}
                for key, value in invoice_pay_dic.items():
                    final_list.append(value)
                    for col_name in final_total_col_list:
                        if total_journal_amount.get(col_name, False):
                            total = total_journal_amount.get(col_name)
                            total += value.get(col_name, 0.0)

                            total_journal_amount.update({col_name: total})
                        else:
                            total_journal_amount.update(
                                {col_name: value.get(col_name, 0.0)})

                # finally make user wise dic here.
                search_user = self.env['res.users'].sudo().search([
                    ('id', '=', user_id)
                ], limit=1)
                if search_user:
                    user_data_dic.update({
                        search_user.name: {'pay': final_list,
                                           'grand_total': total_journal_amount}
                    })

                for col_name in final_total_col_list:
                    j_total = 0.0
                    j_total = total_journal_amount.get(col_name, 0.0)
                    j_total += grand_journal_dic.get(col_name, 0.0)
                    grand_journal_dic.update({col_name: j_total})

            j_refund = j_refund * -1
            grand_journal_dic.update({'Refund': j_refund})

        data.update({
            'date_start': data['date_start'],
            'date_end': data['date_end'],
            'columns': final_col_list,
            'user_data_dic': user_data_dic,
            'currency': currency,
            'grand_journal_dic': grand_journal_dic,
        })

        configs = self.env['pos.config'].browse(data['config_ids'])
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
        
        # for product in self.env['product.product'].search([('type','=','product'),('sale_ok','=',True)]):
        #     product_qty_available = self.env['product.product'].browse(product.id) 
        #     qty_available = product_qty_available.with_context({'to_date': 'date_end','company_id':self.env.company.id}).qty_available

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
            payments = self.env.cr.dictfetchall()
        else:
            payments = []

        return {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': payments,
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