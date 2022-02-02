# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'POS Product Combo',
    'version': '1.0',
    'summary': """Product can be sold as a Combo in POS
    """,
    'description': """
        Product can be sold as a Combo in POS.
    """,
    'category': 'Point Of Sale',
    'author': 'Aurayan Consulting Services',
    'website': '',
    'depends': ['pos_restaurant', 'imerex_pos_stock_info','era_pos_tax_invoice'],
    'data': [
        'security/ir.model.access.csv',
        'views/point_of_sale.xml',
        'views/product_view.xml',
        'views/pos_config_view.xml',
        'report/combo_invoice_report.xml',
    ],
    'qweb': [
        'static/src/xml/pos.xml',
    ],
    'license': 'OPL-1',
    'auto_install': False,
    'application': True,
    'installable': True,
}
