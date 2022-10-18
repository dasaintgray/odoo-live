from odoo.addons.base_rest.controllers import main

class cBizAPI(main.RestController):
    _inherit = "base.rest.service"
    _root_path = '/api/'
    _collection_name = 'cbiz.services.api'
    _default_auth = 'api_key'
    _description = """
    cBizAPI
    """