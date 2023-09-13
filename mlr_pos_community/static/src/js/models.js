odoo.define('mlr_point_of_sale.models', function (require) { // super point of sale models
"use strict";


    var models = require('point_of_sale.models');
    var { Order, Payment } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const PosBTCPayServerPayment = (Payment) => class PosBTCPayServerPayment extends Payment {
        
        constructor(obj, options) {
            super(...arguments);
        }
        //@override
        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.btcpay_invoice_id = this.btcpay_invoice_id;
            json.btcpay_payment_link_qr_code = this.btcpay_payment_link_qr_code;
            json.btcpay_payment_link = this.btcpay_payment_link;
            json.invoiced_sat_amount = this.invoiced_sat_amount;
            json.conversion_rate = this.conversion_rate;
            return json;
        }
        //@override
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.btcpay_invoice_id = json.btcpay_invoice_id;
            this.btcpay_payment_link = json.btcpay_payment_link;
            this.conversion_rate = json.conversion_rate;
            const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
            let qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write('lightning:'+json.btcpay_payment_link, 150, 150));
            this.btcpay_payment_link_qr_code = "data:image/svg+xml;base64,"+ window.btoa(qr_code_svg);
            this.invoiced_sat_amount = json.invoiced_sat_amount;
        }
    }
    Registries.Model.extend(Payment, PosBTCPayServerPayment);

});
