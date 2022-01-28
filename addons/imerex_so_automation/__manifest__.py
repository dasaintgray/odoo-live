# -*- coding: utf-8 -*-
{
    'name' : 'SO Automation',
    'version' : '1.0',
    'author':'Imerex',
    'category': 'Sales',
    'maintainer': 'Imerex',
    'summary': """Enable automatic workflow for SO with SO confirmation.""",
    'description': """

        You can directly create invoice and set done to delivery order by a single click

    """,
    'website': 'https://www.imerex.com.ph/',
    'license': 'LGPL-3',
    'support':'jtecson@imerex.com.ph',
    'depends' : ['sale_management','stock'],
    'data': [
        'views/stock_warehouse.xml',
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,

}
