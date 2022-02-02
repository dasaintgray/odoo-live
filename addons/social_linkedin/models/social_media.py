# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import hashlib
import requests
from werkzeug.urls import url_encode, url_join

from odoo import _, models, fields
from odoo.exceptions import UserError


class SocialMediaLinkedin(models.Model):
    _inherit = 'social.media'

    _LINKEDIN_ENDPOINT = 'https://api.linkedin.com/v2/'

    # Control the fields returned by the LinkedIn API
    # https://docs.microsoft.com/en-us/linkedin/shared/api-guide/concepts/decoration
    _LINKEDIN_ORGANIZATION_PROJECTION = 'localizedName,vanityName,logoV2(original~:playableStreams)'
    _LINKEDIN_PERSON_PROJECTION = 'id,localizedFirstName,localizedLastName,vanityName,profilePicture(displayImage~:playableStreams)'
    _LINKEDIN_TAG_PROJECTION = 'start,length,value(com.linkedin.common.MemberAttributedEntity(member~(vanityName)),com.linkedin.common.CompanyAttributedEntity(company~(vanityName)))'
    _LINKEDIN_COMMENT_PROJECTION = 'id,comments,$URN,content,message(text,attributes*(%s)),likesSummary,created(time, actor~person(%s)~organization(%s)),commentsSummary(totalFirstLevelComments,selectedComments(~comment(id,$URN,created)) )' % (_LINKEDIN_TAG_PROJECTION, _LINKEDIN_PERSON_PROJECTION, _LINKEDIN_ORGANIZATION_PROJECTION)
    _LINKEDIN_STREAM_POST_PROJECTION = 'id,totalShareStatistics,created(time), author~person(%s)~organization(%s), specificContent(com.linkedin.ugc.ShareContent(shareCommentary(text), media(originalUrl)))' % (_LINKEDIN_PERSON_PROJECTION, _LINKEDIN_ORGANIZATION_PROJECTION)

    media_type = fields.Selection(selection_add=[('linkedin', 'LinkedIn')])

    def _compute_linkedin_csrf(self):
        return hmac.new(
            self.env['ir.config_parameter'].sudo().get_param('database.secret').encode('utf-8'),
            str((self.env.cr.dbname, 'social.account', self.id)).encode('utf-8'), hashlib.sha256).hexdigest()

    def action_add_account(self):
        self.ensure_one()

        if self.media_type != 'linkedin':
            return super(SocialMediaLinkedin, self).action_add_account()

        linkedin_use_own_account = self.env['ir.config_parameter'].sudo().get_param('social.linkedin_use_own_account')
        linkedin_app_id = self.env['ir.config_parameter'].sudo().get_param('social.linkedin_app_id')
        linkedin_client_secret = self.env['ir.config_parameter'].sudo().get_param('social.linkedin_client_secret')

        if linkedin_app_id and linkedin_client_secret and linkedin_use_own_account:
            return self._add_linkedin_accounts_from_configuration(linkedin_app_id)
        else:
            return self._add_linkedin_accounts_from_iap()

    def _add_linkedin_accounts_from_configuration(self, linkedin_app_id):
        params = {
            'response_type': 'code',
            'client_id': linkedin_app_id,
            'redirect_uri': self._get_linkedin_redirect_uri(),
            'state': self._compute_linkedin_csrf(),
            'scope': 'r_liteprofile r_emailaddress w_member_social rw_organization_admin w_organization_social r_organization_social'
        }

        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.linkedin.com/oauth/v2/authorization?%s' % url_encode(params),
            'target': 'self'
        }

    def _add_linkedin_accounts_from_iap(self):
        o_redirect_uri = url_join(
            self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            'social_linkedin/callback')

        social_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'social.social_iap_endpoint',
            self.env['social.media']._DEFAULT_SOCIAL_IAP_ENDPOINT
        )

        iap_add_accounts_url = requests.get(url_join(social_iap_endpoint, 'iap/social_linkedin/add_accounts'), params={
            'state': self._compute_linkedin_csrf(),
            'scope': 'r_liteprofile r_emailaddress w_member_social rw_organization_admin w_organization_social r_organization_social',
            'o_redirect_uri': o_redirect_uri,
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        }, timeout=10).text

        if iap_add_accounts_url == 'unauthorized':
            raise UserError(_("You don't have an active subscription. Please buy one here: %s") % 'https://www.odoo.com/buy')
        elif iap_add_accounts_url == 'linkedin_missing_configuration' or iap_add_accounts_url == 'missing_parameters':
            raise UserError(_("The url that this service requested returned an error. Please contact the author of the app."))

        return {
            'type': 'ir.actions.act_url',
            'url': iap_add_accounts_url,
            'target': 'self'
        }

    def _get_linkedin_redirect_uri(self):
        return url_join(
            self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            'social_linkedin/callback')
