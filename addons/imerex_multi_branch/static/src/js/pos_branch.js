odoo.define('imerex_multi_branch.branch', function(require){
    "use strict";
    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');
    var models = require('point_of_sale.models');
    models.load_fields("pos.config", "branch_id");
    models.load_models({
        model: 'res.branch',
        fields: ['id','name', 'street', 'street2','city','state_id','country_id','email','phone','website'],
        domain: function(self) {return [['id', '=', self.config.branch_id[0] || false]]},
        loaded: function (self, branch) {
            self.branch = branch[0]
            console.log(self.branch);
        },
    });
    const BranchOrderReceipt = OrderReceipt =>
        class extends OrderReceipt {
            get receiptEnv() {
                let receipt_render_env = super.receiptEnv;
                receipt_render_env.branch = []
                receipt_render_env.receipt.branch.street = this.env.pos.branch.street;
                var branch_address = this.env.pos.branch.street;
                if (this.env.pos.branch.city) { branch_address += "-" + this.env.pos.branch.city }
                var branch_state = this.env.pos.company.state_id[1];
                if (this.env.pos.branch.country_id) { branch_state += "-" + this.env.pos.branch.country_id[1] }
                receipt_render_env.receipt.branch_address = branch_address;
                receipt_render_env.receipt.branch_state = branch_state;
                return receipt_render_env;
            }
        };

    Registries.Component.extend(OrderReceipt, BranchOrderReceipt);

    return OrderReceipt;
})