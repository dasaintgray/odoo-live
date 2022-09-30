# See LICENSE file for full copyright and licensing details.

{
    "name": "Imerex - Tracking",
    "version": "0.0.0.1",
    "category": "Hidden",
    "license": "AGPL-3",
    "summary": "ERP customization",
    "author": "James Tecson, Circuit Minds I.T. Business Solutions",
    "website": "https://mrm.imerex.com.ph",
    "maintainer": "Circuit Minds I.T. Business Solutions",
    "depends": ["contacts","sale","component","base_rest","imerex_multi_branch","imerex_erp","account_debit_note"],
    "data": [
            "views/res_config_settings_view.xml",
            "security/ir.model.access.csv"
        ],
    "external_dependencies": {"python": ["jsondiff"]},
    "installable": True,
    "auto_install": False,
}
