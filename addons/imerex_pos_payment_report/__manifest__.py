# -*- coding: utf-8 -*-
# Part of Imerex Group of Companies.
{
    "name": "POS Detailed Summary Report",
    "author": "Imerex",
    "license": "OPL-1",
    "website": "https://www.imerex.com.ph",
    "support": "jtecson@imerex.com.ph",
    "category": "Accounting",
    "summary": "Point Of Sale Payment Report for Imerex",
    "description": """Payment Summary Report for Imerex""",
    "version": "1",
    "depends": ["point_of_sale", "account",'base', 'sale_management', 'purchase', 'stock'],
    "application": True,
    "data": [
        "security/payment_report_security.xml",
            "security/ir.model.access.csv",
            "wizard/payment_report_wizard.xml",
            "report/payment_report.xml",
            "wizard/xls_report_view.xml",
    ],
    "images": ["static/description/background.png", ],
    "auto_install": False,
    "installable": True
}
