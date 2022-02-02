# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    cache_models_ids = fields.Many2many(
        'ir.model',
        string="Models",
        help="Models to make cache in POS.",
    )
