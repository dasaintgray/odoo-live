# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pe_edi_certificate_id = fields.Many2one(
        string="Certificate (PE)", store=True, readonly=False,
        comodel_name='l10n_pe_edi.certificate',
        compute="_compute_l10n_pe_edi_certificate")
    l10n_pe_edi_provider_username = fields.Char(
        string="SOL User",
        help="The username used to login to SUNAT SOL")
    l10n_pe_edi_provider_password = fields.Char(
        string="SOL Password",
        help="The password used to login to SUNAT SOL")
    l10n_pe_edi_provider = fields.Selection(
        selection=[('digiflow', 'Digiflow'), ('sunat', 'SUNAT'), ('iap', 'IAP')],
        string="Electronic Service Provider (ESP)", default="iap",
        help="Selector for the service we are going to use to report the invoices:"
             "DIGIFLOW: With the certified that digiflow provide you, user and password you will report the invoices to them."
             "SUNAT: You will report the invoices directly to them using your own certified, user and password."
             "IAP: This is an odoo service that will send the unsigned documents to a PSE and process their response.")
    l10n_pe_edi_address_type_code = fields.Char(
        string="Address Type Code",
        default="0000",
        help="Code of the establishment that SUNAT has registered.")
    l10n_pe_edi_test_env = fields.Boolean(
        string="Is test OSE environment",
        help='Enable the use of test credentials')

    @api.depends('country_id')
    def _compute_l10n_pe_edi_certificate(self):
        for company in self:
            if company.country_code == 'PE':
                company.l10n_pe_edi_certificate_id = self.env['l10n_pe_edi.certificate'].search(
                    [('company_id', '=', company.id)], order='date_end desc', limit=1)
            else:
                company.l10n_pe_edi_certificate_id = False

    def _localization_use_documents(self):
        # OVERRIDE
        self.ensure_one()
        return self.country_id == self.env.ref('base.pe') or super()._localization_use_documents()
