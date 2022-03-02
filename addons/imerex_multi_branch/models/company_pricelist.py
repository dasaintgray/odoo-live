
from odoo import api, fields, models, _

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    def _default_company(self):
        return self.env.company.id

    company_id = fields.Many2one('res.company', 'Company',
                                default=_default_company
                                )

