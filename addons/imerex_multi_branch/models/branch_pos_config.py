
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import unique

class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _get_branch_id(self):
        return ['&',('id', 'in',self.env.user.branch_ids.ids),('company_id','=',self.env.company.id)]

    branch_id = fields.Many2one("res.branch", string='Branch', store=True,
                                readonly=False, domain=_get_branch_id)
    # picking_type_id = fields.Many2one(domain=_picking_type_check)
    _sql_constraints = [('pos_name_unique', 'unique(name)','POS Name must be unique!')]
    @api.constrains('picking_type_id')
    def picking_type_check(self):
        if self.branch_id:
            if not self.branch_id == self.picking_type_id.branch_id:
                raise ValidationError(_("""The Operation Type "%(picking)s" is not included in the Operations of %(branch)s""",
                    branch = self.branch_id.name,
                    picking = self.picking_type_id.display_name))

    @api.model
    def create(self,values):
        #Branch Validation on POS Configs of Companies with Branch Setup
        pos_config = super(PosConfig, self).create(values)
        self.branch_checking(values)
        return pos_config

    def write(self, vals):
        #Branch Validation on POS Configs of Companies with Branch Setup
        pos_config = super(PosConfig, self).write(vals)
        self.branch_checking(vals)
        #reattach Odoo PosConfig data and code
        return pos_config

    def copy(self):
        #Change name when duplicating PosConfig
        pos_config = super(PosConfig, self).copy({'name': self.name + ' copy'})
        return pos_config

    def branch_checking(self,vals):
        branch_check = self.env['res.branch'].search(['|',('company_id','=',self.company_id.id),('company_id','=',self.env.company.id)]).company_id
        if 'branch_id' in vals:
            if not vals['branch_id'] and self.company_id == branch_check:
                raise ValidationError(_("""The company: %(company)s has branch setup. Please assign a Branch""",
                        company = self.company_id.display_name))
        if not self.branch_id and self.company_id == branch_check:
            raise ValidationError(_("""The company: %(company)s has branch setup. Please assign a Branch""",
                    company = self.company_id.display_name))

    @api.onchange('branch_id')
    def domain_picking_type_id(self):
        if self.branch_id:
            domain = ['&',('company_id','=', self.env.company.id),('branch_id','=',self.branch_id.id)]
        else:
            domain = [('company_id','=', self.env.company.id)]
        domain_return = {'domain': {'picking_type_id': domain}}
        return domain_return

