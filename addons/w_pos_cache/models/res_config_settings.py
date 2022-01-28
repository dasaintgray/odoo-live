# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cache_models_ids = fields.Many2many(
        'ir.model',
        string="Models",
        help="Models to make cache in POS.",
        related='company_id.cache_models_ids',
        readonly=False,
    )
