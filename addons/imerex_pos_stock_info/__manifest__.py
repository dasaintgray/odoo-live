# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "POS Stock Info",
    "author": "Imerex",
    "website": "https://www.imerex.com.ph",
    "support": "jtecson@imerex.com.ph",
    "category": "Point of Sale",
    "license": "OPL-1",
    "summary": "POS Stock Info",
    "description": """This module allows you to displays product stock quantities at the point of sale.""",
    "version": "1.2",
    "depends": ["point_of_sale"],
    "application": True,
    "data": [
        'views/assets.xml',
        'views/pos_config.xml',
    ],
    "qweb": ["static/src/xml/*.xml"],
    "auto_install": False,
    "installable": True,
}
