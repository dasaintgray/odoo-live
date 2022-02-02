# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Wedoo| Pos Cache',
    'author': 'Wedoo ©',
    'category': 'Tools',
    'sequence': 50,
    'summary': "Enable a cache on pos models for a lower POS loading time.",
    'website': 'https://www.wedoo.tech',
    'version': '14.0.0.0',
    'license': 'AGPL-3',
    'description': """
This creates a cache per POS config. It drastically lowers the
time it takes to load a POS session with a lot of model items.
    """,
    'depends': [
        'base',
        'point_of_sale',
    ],
    'data': [
        'data/pos_cache_data.xml',
        'security/ir.model.access.csv',
        'views/pos_cache_views.xml',
        'views/pos_cache_templates.xml',
        'views/res_config_settings_view.xml',
    ],
    'images': [
        'static/description/stage_description.png',
        'static/description/stage_screenshot.png',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'price': "32",
    "currency": "EUR",
}

