from odoo import models, fields

class Branch(models.Model):
    """res branch"""
    _name = "res.branch"
    _description = 'Company Branches'
    _order = 'name'

    name = fields.Char(string='Branch', required=True, store=True)
    receipt_name = fields.Char(string ='Company Name in POS Receipts')
    receipt_branchname = fields.Char(string='Branch Name in POS Receipts')
    ksa_address = fields.Char(string="Arabian Address")
    company_id = fields.Many2one('res.company', required=True, string='Company')
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    cargo_branch_id = fields.Integer(string="CTrack ID")
    state_id = fields.Many2one(
        'res.country.state',
        string="Fed. State", domain="[('country_id', '=?', country_id)]"
    )
    country_id = fields.Many2one('res.country',  string="Country")
    email = fields.Char(store=True, )
    phone = fields.Char(store=True)
    website = fields.Char(readonly=False)
    twitter = fields.Char()
    facebook = fields.Char()

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The Branch name must be unique !')
    ]

    def copy(self):
        branch = super(Branch,self).copy({'name': self.name + ' copy'})
        return branch
