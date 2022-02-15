odoo.define('imerex_multi_branch.branch', function(require){
    "use strict";
    var models = require('point_of_sale.models');
    models.load_fields("pos.config", "branch_id");
    models.load_models({
        model: 'res.branch',
        fields: ['id', 'street', 'street2','city','state_id','country_id','email','phone','website'],
        domain: [['id', '=', this.pos.config.branch_id[0]]],
        ids:    function(self){ return [self.session.user_context.allowed_company_ids[0]]; },
        loaded: function(self,companies){ self.company = companies[0]; },
    })


    console.log(models);
    let _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize:function(attr,options){
            var line=_super_order.initialize.apply(this,arguments);
            this.branch_id= this.pos.config.branch_id;
            console.log(this.branch_id)
        }
    })
})