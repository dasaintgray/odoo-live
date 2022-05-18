from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    imerex_circuittrack_gw = fields.Char("Gateway URL", config_parameter='imerex_circuittrack_gw', groups='base.group_system')
    imerex_circuittrack_jwt = fields.Char("JWT URL", config_parameter='imerex_circuittrack_gw', groups='base.group_system')
    imerex_api_username = fields.Char("Username", config_parameter='imerex_api_username', groups='base.group_system')
    imerex_api_password = fields.Char("Password", config_parameter='imerex_api_password', groups='base.group_system')