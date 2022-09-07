# See LICENSE file for full copyright and licensing details.
"""Module For City."""

from odoo import api, fields, models, exceptions
from odoo.tools.misc import unique
from odoo.exceptions import UserError

class City(models.Model):
    """Model City."""

    _name = "imerex_erp.city"
    _description = "City"

    def name_get(self):
        """Method Name Get."""
        res = []
        for line in self:
            name = line.name
            if line.state_id:
                name = "%s, %s" % (name, line.state_id.name)
            if line.country_id:
                name = "%s, %s" % (name, line.country_id.name)
            if line.zip:
                name = "%s %s" % (name, line.zip)
            res.append((line["id"], name))
        return res

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Method Name Search."""
        if args is None:
            args = []
        args = ["|", ("zip", operator, name), ("name", operator, name)]
        rec_ids = self.search(args, limit=limit)
        return rec_ids.name_get()

    state_id = fields.Many2one("res.country.state", "State", index=True)
    name = fields.Char("City", size=64, required=True, index=True)
    zip = fields.Char("ZIP", size=64)
    """
    _sql_constraints = [('zip_unique', 'unique(zip)','Zip must be unique!')]
    #unique value SQL constraint
    zip = fields.Char("ZIP", size=64, index=True)
    #indexed unique
    """
    country_id = fields.Many2one("res.country", "Country", index=True)
    code = fields.Char("City Code", size=64, help="The official code for the city")

class CountryState(models.Model):
    """Model Country State."""

    _inherit = "res.country.state"

    city_ids = fields.One2many("imerex_erp.city", "state_id", "Cities")

class Company(models.Model):
    """Model Company
    _get_company_address_fields - Addendum to original def
    _compute_address - res.company def
    """

    _inherit = "res.company"

    brgy = fields.Char("Barangay or Area", size=64, compute='_compute_address', inverse='_imerex_inverse_brgy')
    city_id = fields.Many2one('imerex_erp.city', compute='_compute_address', inverse='_imerex_inverse_city')
    cargo_branch_id = fields.Char("Cargo Branch ID Reference", size=5)
    hashrow = fields.Char("HashRow", size=64)
    def _get_company_address_field_names(self):
        return ['street', 'street2', 'city', 'zip', 'state_id', 'country_id','brgy', 'city_id']

    def _imerex_inverse_city(self):
        for company in self:
            company.partner_id.city_id = company.city_id
            company.partner_id.city = company.city_id.name

    def _imerex_inverse_brgy(self):
        for company in self:
            company.partner_id.brgy = company.brgy
    
    @api.onchange("city_id")
    def onchange_city_id(self):
        if self.city_id:
            self.zip = self.state_id = self.country_id = self.city = False
            self.zip = self.city_id.zip
            self.city = self.city_id.name
            state = self.city_id.state_id
            self.state_id = state.id
            if state.country_id:
                self.country_id = state.country_id.id
    
class Followers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def create(self, vals):
        if 'res_model' in vals and 'res_id' in vals and 'partner_id' in vals:
            dups = self.env['mail.followers'].search([('res_model', '=',vals.get('res_model')),('res_id', '=', vals.get('res_id')),('partner_id', '=', vals.get('partner_id'))])
            if len(dups):
                for p in dups:
                    p.unlink()
        res = super(Followers, self).create(vals)
        return res