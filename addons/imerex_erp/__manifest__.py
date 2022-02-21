# See LICENSE file for full copyright and licensing details.

{
    "name": "Imerex - Customization",
    "version": "0.0.0.1",
    "category": "Hidden",
    "license": "AGPL-3",
    "summary": "ERP customization",
    "author": "James Tecson, Circuit Minds I.T. Business Solutions",
    "website": "https://mrm.imerex.com.ph",
    "maintainer": "Circuit Minds I.T. Business Solutions",
    "depends": ["contacts","sale","account","product","component","base_rest"],
    "data": [
        "views/city.xml",
        "views/product_product.xml",
        "views/product_template.xml",
        "views/res_partner.xml",
        "views/sale_order.xml",
        "views/jwt_schedule.xml",
        "security/ir.model.access.csv"
        ],
    "external_dependencies": {"python": ["jsondiff"]},
    "installable": True,
    "auto_install": False,
}
