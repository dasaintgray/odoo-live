# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json
from ast import literal_eval
import threading
import logging

from odoo import models, fields, api, registry, SUPERUSER_ID

_logger = logging.getLogger(__name__)


class PosCache(models.Model):
    _name = 'pos.cache'
    _description = 'Point of Sale Cache'

    model_id = fields.Many2one('ir.model', ondelete='cascade', required=True)
    domain_value = fields.Text(required=True)
    fields_names = fields.Text(required=True)

    config_id = fields.Many2one('pos.config', ondelete='cascade', required=True)
    compute_user_id = fields.Many2one('res.users', 'Cache compute user', required=True)
    cache = fields.Binary(attachment=True)

    @api.model
    def refresh_all_caches(self):
        self.env['pos.cache'].search([]).refresh_cache()

    @api.model
    def refresh_cache_by_model(self, model):
        self.env['pos.cache'].search([('model_id.model', '=', model)]).refresh_cache()

    def refresh_cache(self):
        for cache in self:
            ModelObj = self.env[cache.model_id.model].with_user(cache.compute_user_id.id)
            records = ModelObj.search(cache.get_domain() or [])
            records_ctx = records.with_context(lang=cache.compute_user_id.lang)
            res = records_ctx.read(cache.get_fields())
            cache.write({
                'cache': base64.encodestring(json.dumps(res, default=str).encode('utf-8')),
            })

    @api.model
    def get_domain(self):
        return literal_eval(self.domain_value)

    @api.model
    def get_fields(self):
        return literal_eval(self.fields_names)

    @api.model
    def get_cache(self, domain, fields):
        if not self.cache or domain != self.get_domain() or fields != self.get_fields():
            self.domain_value = str(domain)
            self.fields_names = str(fields)
            self.refresh_cache()
        return json.loads(base64.decodestring(self.cache).decode('utf-8'))


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # Use a related model to avoid the load of the cache when the pos load his config
    cache_ids = fields.One2many('pos.cache', 'config_id')

    def _get_cache_for_user(self, model):
        pos_cache = self.env['pos.cache']
        cache_for_user = pos_cache.search(
            [('id', 'in', self.cache_ids.ids), ('compute_user_id', '=', self.env.uid), ('model_id.model', '=', model)]
        )

        if cache_for_user:
            return cache_for_user[0]
        else:
            return None

    def get_records_from_cache(self, fields, domain, model):
        cache_for_user = self._get_cache_for_user(model)

        if cache_for_user:
            return {'model': model, 'data': cache_for_user.get_cache(domain, fields)}
        else:
            pos_cache = self.env['pos.cache']
            pos_cache.create({
                'config_id': self.id,
                'domain_value': str(domain),
                'fields_names': str(fields),
                'compute_user_id': self.env.uid,
                'model_id': self.env['ir.model'].search([('model', '=', model)], limit=1).id
            })
            new_cache = self._get_cache_for_user(model)
            return {'model': model, 'data': new_cache.get_cache(domain, fields)}

    def delete_cache(self):
        # throw away the old caches
        self.cache_ids.unlink()

    def get_models_to_cache(self):
        return self.env.user.company_id.cache_models_ids.mapped('model')


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def write(self, vals):
        result = super(BaseModel, self).write(vals)
        if self._name in self.env.user.company_id.cache_models_ids.mapped('model'):
            self._cr.commit()
            threaded_calculation = threading.Thread(target=self.update_w_cache, args=(self._name,))
            threaded_calculation.start()
        return result

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, val_list):
        result = super(BaseModel, self).create(val_list)
        if self._name in self.env.user.company_id.cache_models_ids.mapped('model'):
            self._cr.commit()
            threaded_calculation = threading.Thread(target=self.update_w_cache, args=(self._name,))
            threaded_calculation.start()
        return result

    def update_w_cache(self, model_name):
        dbname = self.env.cr.dbname
        db_registry = registry(dbname)
        _context = self._context
        with api.Environment.manage(), db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, _context)
            try:
                _logger.info('Start to update %s pos cache' % model_name)
                env['pos.cache'].refresh_cache_by_model(model_name)
                _logger.info('End to update %s pos cache' % model_name)
            except Exception as e:
                _logger.info('An error ocurred trying to update %s pos cache: %s' % (model_name, str(e)))
                self._cr.rollback()
                self._cr.close()
