# -*- coding: utf-8 -*-
{
    'name': 'POS Default Customer',
    'summary': "Default Customer in POS",
    'description': 'Default Customer in POS',

    'author': 'James Tecson',
    'website': 'https://www.imerex.com.ph/',
    "support": "jtecson@imerex.com.ph",

    'category': 'Point of Sale',
    'version': '1',
    'depends': ['point_of_sale'],

    'data': [
        'views/assets.xml',
        'views/pos_config_view.xml',
    ],

    'license': "OPL-1",

    'installable': True,
    'application': True,

    'pre_init_hook': 'pre_init_check',
}
