# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api
from odoo.exceptions import ValidationError
import requests
import json

class PosOrderInherit(models.Model):
    _inherit = "pos.order"

    @api.model 
    def _process_order(self, order, draft, existing_order): #super function to update orders on btcpay journal, not sure if used
        print( '_process_order_process_order inherti')
        res = super()._process_order(order, draft, existing_order)
        pos_order_obj = self.search([('id', '=', res)])
        account_journal_obj = self.env['account.journal'].search([("use_btcpay_server","=",True)])
        pos_payment_method_obj = self.env['pos.payment.method'].search([("journal_id","in",account_journal_obj.ids)])
        return res
    
    @api.model
    def _payment_fields(self, order, ui_paymentline): #super function to update payment fields
        fields = super(PosOrderInherit, self)._payment_fields(
            order, ui_paymentline)
        pay_method = self.env['pos.payment.method'].search(
            [('id', '=', int(ui_paymentline['payment_method_id']))])
        if pay_method != False: # if there is a payment method
            if pay_method.journal_id.use_btcpay_server: # if the method is connected to the btcpay journal update the appropriate fields
                fields.update({
                    'btcpay_invoice_id': ui_paymentline.get('btcpay_invoice_id'),
                    'btcpay_payment_link': ui_paymentline.get('btcpay_payment_link'),
                    'invoiced_sat_amount': ui_paymentline.get('invoiced_sat_amount'),
                    'conversion_rate': ui_paymentline.get('conversion_rate'),
                })
        return fields

    @api.model
    def _get_fields_for_payment_lines(self):
        payment_fields = super()._get_fields_for_payment_lines()
        return payment_fields + [
            'btcpay_invoice_id',
            'btcpay_payment_link',
            'btcpay_payment_link_qr_code',
            'invoiced_sat_amount',
            'conversion_rate'
            ]


    def get_auto_conversion_rate(self): #only used for the get conversion rate in the systray
        try:
            record_search = self.env['btcpay.server.instance'].search([('state', '=', 'active')])
            base_url = record_search.mapped('server_url')[0]
            store_id = record_search.mapped('store_id')[0]
            api_key = record_search.mapped('api_key')[0]
            server_url = base_url + "/api/v1/stores/" + store_id + "/rates"
            headers = {"Authorization": "Token %s" % (api_key)}
            response = requests.request(method="GET", url=server_url, headers=headers)
            response_json = response.json()
            result = response_json[0].get('rate') if response.status_code == 200 else None
            return result
        except Exception as e:
            raise UserError(_("Get Conversion Rate: %s", e.args))
