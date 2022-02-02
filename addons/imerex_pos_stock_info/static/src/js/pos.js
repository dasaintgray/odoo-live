odoo.define('imerex_pos_stock_info.pos', function (require) {
    'use strict';

    var models = require("point_of_sale.models");
    var DB = require('point_of_sale.DB');
    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const Registries = require("point_of_sale.Registries");

    models.load_fields('product.product', ["is_combo","type","sub_combo_product_line_ids"])

    models.load_models({
        model: 'product.product',
        fields: ['id', 'qty_available', 'virtual_available'],
        domain: [['available_in_pos', '=', true]],
        loaded: function (self, all_on_hand_qty) {
            _.each(all_on_hand_qty, function (product) {
                self.db.on_hand_qty[product['id']] = [product['qty_available'], product['virtual_available'],0,0]
            })
        }
    })
    DB.include({
        init: function (options) {
            this._super(options);
            this.on_hand_qty = {}
        },
    })

    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        set_quantity: function (quantity, keep_price) {
            _super_orderline.set_quantity.call(this, quantity, keep_price)
            var quant = parseFloat(quantity) || 0;
            var prod;
            let self = this;
            let checked_req_dom = $("input[name='product']:checked");
            let checked_un_req_dom = $("input[name='un_req_products']:checked")
            if (self.product.is_combo == true) {
                let product_ids_req = _.map(checked_req_dom, function(value){
                    return $(value).attr('id');
                });
                let product_ids_unreq = _.map(checked_un_req_dom, function(value){
                    return $(value).attr('id');
                });
                prod = _.uniq(_.union(
                    _.map(product_ids_req, function(value){return Number(value.split('id')[0])}),
                    _.map(product_ids_unreq, function(value){return Number(value.split('id')[0])})
                    ));
                if (self.all_selected_product_id){
                    prod = _.map(self.all_selected_product_id,function(value){return Number(value.split('id')[0])})
                }
            }
            else {
                prod = [self.product.id];
            }

            let in_orderline = [];
            let summation = [];
            var orderedlines = this.pos.get_order().get_orderlines();
            if (orderedlines) {
                _.each(this.pos.get_order().get_orderlines(), function(val){
                    var combo_sub_products;
                    if (val.all_selected_product_id) {
                        combo_sub_products = _.map(val.all_selected_product_id,function(value){return Number(value.split('id')[0])})
                    }
                    in_orderline.push({
                        'id': val.id,
                        'cid': val.cid,
                        'product_id': val.product.id,
                        'quantity': val.quantity,
                        'combo_sub_products': combo_sub_products
                    })
                })
            }
            if (self.pos.config.sh_enable_on_hand_qty) {
                _.each(in_orderline, function(val){
                    if (val.combo_sub_products) {
                        _.each(val.combo_sub_products, function(valcombo){
                            summation.push({
                                'product_id': valcombo,
                                'total_qty': val.quantity
                            })
                        });
                    }
                    summation.push({
                        'product_id': val.product_id,
                        'total_qty': val.quantity
                    })
                });


                if (!self.qty) {
                    _.each(prod, function(val) {
                        summation.push({
                            'product_id': val,
                            'total_qty': quant
                        });
                    });
                    if(self.is_combo == true){
                        summation.push({
                            'product_id': self.product.id,
                            'total_qty': quant
                        });
                    }
                }
                var totalPerType = {};
                for (var i = 0, len = summation.length; i < len; ++i) {
                    totalPerType[summation[i].product_id] = totalPerType[summation[i].product_id] || 0;
                    totalPerType[summation[i].product_id] += summation[i].total_qty;
                }
                var out = _.map(totalPerType, function (total_qty, product_id) {
                    return {'product_id': product_id, 'quantity': total_qty};
                });
                _.each(out, function(val){
                    if (document.getElementById(val.product_id)) {
                        document.getElementById(val.product_id).innerHTML = self.pos.db.on_hand_qty[val.product_id][0] - val.quantity
                        self.pos.db.combo_qty[val.product_id][0] = self.pos.db.on_hand_qty[val.product_id][0] - val.quantity
                        }
                    if (document.getElementsByName(val.product_id).length > 0) {
                        document.getElementsByName(val.product_id)[0].innerHTML = self.pos.db.on_hand_qty[val.product_id][1] - val.quantity
                        self.pos.db.combo_qty[val.product_id][1] = self.pos.db.on_hand_qty[val.product_id][1] - val.quantity
                        }
                })  
            }
            // if (this.pos.config.sh_enable_on_hand_qty) {
            //     if (this.pos.config.sh_manage_stock == "on_hand_qty") {
            //         if (this.product.type == 'product') {
            //             on_hand = this.pos.db.on_hand_qty[this.product.id][0] - quant
            //         }
            //     }
            //     else if (this.pos.config.sh_manage_stock == "available_qty") {
            //         if (this.product.type == 'product') {
            //             virtual_qty = this.pos.db.on_hand_qty[this.product.id][1] - quant
            //         }
            //     }
            //     else {
            //         if (this.product.type == 'product') {
            //             on_hand = this.pos.db.on_hand_qty[this.product.id][0] - quant
            //             virtual_qty = this.pos.db.on_hand_qty[this.product.id][1] - quant
            //         }
            //     }
            //     if (document.getElementById(this.product.id)) {
            //         this.pos.db.combo_qty[this.product.id][0] = on_hand
            //         document.getElementById(this.product.id).innerHTML = this.pos.db.combo_qty[this.product.id][0]      
            //     }
            //     if (document.getElementsByName(this.product.id).length > 0) {
            //         document.getElementsByName(this.product.id)[0].innerHTML = virtual_qty
            //     }
        }
    });

    const ShPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            async validateOrder(isForceValidate) {
                var self = this
                if (this.env.pos.config.sh_enable_on_hand_qty) {
                    var all_on_hand_qty = this.env.pos.db.on_hand_qty
                    var orderlines = self.env.pos.get_order().get_orderlines()
                    console.log(all_on_hand_qty)
                    _.each(all_on_hand_qty, function (key, on_had_qty) {
                        _.each(orderlines, function (line) {
                            if (line) {
                                if (on_had_qty == line.product.id) {
                                    console.log(line)
                                    if (line.product.type == 'product') {
                                        key[0] = key[0] - line.quantity
                                        key[1] = key[1] - line.quantity
                                        if (line.all_selected_product_id) {
                                            let combo_sub = _.map(line.all_selected_product_id,function(value){return Number(value.split('id')[0])})
                                            _.each(combo_sub, function(val) { 
                                                all_on_hand_qty[val][0] = all_on_hand_qty[val][0] - line.quantity
                                                all_on_hand_qty[val][1] = all_on_hand_qty[val][1] - line.quantity
                                            })
                                        }
                                    }
                                }
                            }
                        })
                    })
                }
                super.validateOrder(isForceValidate)
            }
        }
    Registries.Component.extend(PaymentScreen, ShPaymentScreen)
});
