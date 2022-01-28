odoo.define('pos_cache.pos_cache', function (require) {
"use strict";

var models = require('point_of_sale.models');
var core = require('web.core');
var rpc = require('web.rpc');
var _t = core._t;

var posmodel_super = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    load_server_data: function () {
        var self = this;
        var given_config = new RegExp('[\?&]config_id=([^&#]*)').exec(window.location.href);
        var config_id = given_config && given_config[1] && parseInt(given_config[1]) || false;
        var loaded = new Promise(function (resolve, reject) {
            rpc.query({
                model: 'pos.config',
                method: 'get_models_to_cache',
                args: [config_id],
            }).then(function (models) {
                var models_data = []
                for(var i = 0, len = models.length; i < len; i++){
                    var index = _.findIndex(self.models, function (model) {
                        return model.model === models[i];
                    });
                    if (index != -1){
                        models_data.push(self.models[index]);
                    }else{
                        console.log('Model not found in pos: ' + models[i]);
                    }
                    //models_data.push(self.models[index]);
                    // We don't want to load product.product the normal
                    // uncached way, so get rid of it.
                    if (index !== -1) {
                        self.models.splice(index, 1);
                    }
                    
                }
                posmodel_super.load_server_data.apply(self, arguments).then(function () {
                    var p_calls = []
                    for(var i = 0, len = models_data.length; i < len; i++){
                        // Give both the fields and domain to pos_cache in the
                        // backend. This way we don't have to hardcode these
                        // values in the backend and they automatically stay in
                        // sync with whatever is defined (and maybe extended by
                        // other modules) in js.
                        var c_m_data = models_data[i];
                        var fields =  typeof c_m_data.fields === 'function'  ? c_m_data.fields(self)  : c_m_data.fields;
                        var domain =  typeof c_m_data.domain === 'function'  ? c_m_data.domain(self)  : c_m_data.domain;
                        //self.chrome.loading_message(_t('Loading cached models: ') + models.join(), 1);
                        var records = rpc.query({
                            model: 'pos.config',
                            method: 'get_records_from_cache',
                            args: [self.pos_session.config_id[0], fields, domain, c_m_data.model],
                        });
                        records.then(function (result) {
                            var local_c_m_data = _.findWhere(self.models, {'model': result.model});
                            return local_c_m_data.loaded(self, result.data);
                        });
                        p_calls.push(records);
                        self.models.push(c_m_data);
                    }
                    Promise.all(p_calls).then(function () {
                        resolve();
                    });
                });
            });
       });
       return loaded;
    },
});

});
