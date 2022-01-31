#Res Partner modification

from odoo import api, fields, models, exceptions
from odoo.tools.misc import unique
from odoo.exceptions import UserError

class ResPartner(models.Model):
    """Model Res Partner."""

    _inherit = "res.partner"

    brgy = fields.Char("Barangay or Area", size=64)
    city_id = fields.Many2one("imerex_erp.city", "City Address")
    shipper_id = fields.Char("Shipper ID", size=64)
    hashrow = fields.Char("HashRow", size=64)
    _sql_constraints = [('shipper_id_unique', 'unique(shipper_id)','shipper_id must be unique!')]
    type = fields.Selection(selection_add=[('shipper','Shipper'),('consignee', 'Consignee'),('invoice',)],
            string='Address Type',
            default='contact',
            help="Used to select automatically the right address according to the context in sales and purchases documents.")

    @api.onchange("city_id")
    def onchange_city_id(self):
        """Method Onchange."""
        if self.city_id:
            self.zip = self.state_id = self.country_id = self.city = False
            self.zip = self.city_id.zip
            self.city = self.city_id.name
            state = self.city_id.state_id
            self.state_id = state.id
            if state.country_id:
                 self.country_id = state.country_id.id