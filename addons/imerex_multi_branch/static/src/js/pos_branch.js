odoo.define('imerex_multi_branch.branch', function(require){
    "use strict";
    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');
    var models = require('point_of_sale.models');
    models.load_fields("pos.config", "branch_id");
    models.load_models({
        model: 'res.branch',
        fields: ['id','name','receipt_name','receipt_branchname','ksa_address', 'street', 'street2','city','state_id','country_id','email','phone','website','twitter','facebook','mobile','whatsapp'],
        domain: function(self) {return [['id', '=', self.config.branch_id[0] || false]]},
        loaded: function (self, branch) {
            if (branch){
                self.branch = branch[0]
                console.log(self.branch);
            }
        },
    });
    const BranchOrderReceipt = OrderReceipt =>
        class extends OrderReceipt {
            get receiptEnv() {
                let receipt_render_env = super.receiptEnv;
                if (this.env.pos.branch){
                    receipt_render_env.receipt.branch = this.env.pos.branch
                    var branch_address = this.env.pos.branch.street;
                    var branch_state = ''
                    if (this.env.pos.branch.state_id[1]) { branch_state = this.env.pos.branch.state_id[1] }
                    if (this.env.pos.branch.street2) { branch_address += "," + this.env.pos.branch.street2 }                 
                    if (this.env.pos.branch.city) { branch_address += "-" + this.env.pos.branch.city }
                    if (this.env.pos.branch.country_id && branch_state == '' ) { branch_state += this.env.pos.branch.country_id[1]}
                    else if (this.env.pos.branch.country_id) {branch_state += "-" + this.env.pos.branch.country_id[1]}
                    receipt_render_env.receipt.branch_address = branch_address;
                    receipt_render_env.receipt.branch_state = branch_state;
                }
                return receipt_render_env;
            }
        };

    Registries.Component.extend(OrderReceipt, BranchOrderReceipt);
    return OrderReceipt;
})