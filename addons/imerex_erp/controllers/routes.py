from odoo.addons.base_rest.controllers import main
# class JWTAuth(main.RestController):
#     _inherit = "base.rest.service"
#     _root_path = '/jwt/'
#     _collection_name = 'cbiz.services.jwt'
#     _default_auth = 'public'
#     _description = """
#     JWT Auth
#     """

class cBizAPI(main.RestController):
    _inherit = "base.rest.service"
    _root_path = '/api/'
    _collection_name = 'cbiz.services.api'
    _default_auth = 'public'
    _description = """
    cBizAPI
    """