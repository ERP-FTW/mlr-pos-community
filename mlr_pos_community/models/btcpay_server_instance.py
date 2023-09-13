# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError
import requests, logging, json

_logger = logging.getLogger(__name__)


class BTCPayServerInstance(models.Model):
    _name = 'btcpay.server.instance'
    _description = 'BTCPay Server Instance'

    name = fields.Char(string='Name')
    btcpay_company_name = fields.Char(string='Company Name') #added to lightning transaction description for customer reference
    server_url = fields.Char(string='Server URL')
    api_key = fields.Char(string='API Key') #use account API key not store API key
    store_id = fields.Char(string='Store ID')
    state = fields.Selection( #state of instance, should only be one active one at a time
        [("draft", "Not Confirmed"), ("active", "Active"), ("inactive", "Inactive")],
        default="draft",
        string="State",
    )
    conversion_rate_source = fields.Char(string='Conversion Rate', readonly=True) #should be conversion rate source
    expiration_minutes = fields.Integer('Expiration Minutes') #seconds for lightning invoice, converted in function


    def action_get_conversion_rate_source(self): #gets conversion rate source as set on BTCpay server
        try:
            server_url = self.server_url + "/api/v1/stores/" + self.store_id + "/rates/configuration"
            headers = {"Authorization": "Token %s" % (self.api_key)}
            response = requests.request(method="GET", url=server_url, headers=headers)
            response_json = response.json()
            result = response_json['preferredSource'] if response.status_code == 200 else None
            return result
        except Exception as e:
            raise UserError(_("Get Conversion Rate Source: %s", e.args))

    def action_get_conversion_rate(self): #obtains conversion rate from BTCpay server
        try:
            server_url = self.server_url + "/api/v1/stores/" + self.store_id + "/rates"
            headers = {"Authorization": "Token %s" % (self.api_key)}
            response = requests.request(method="GET", url=server_url, headers=headers)
            response_json = response.json()
            result = response_json[0]['rate'] if response.status_code == 200 else None
            return result
        except Exception as e:
            raise UserError(_("Get Conversion Rate: %s", e.args))

    def get_amount_sats(self, pos_payment_obj): #obtains amount of satoshis to invoice by calling action_get_conversion_rate and and doing the math, returns dict of both values
        try:
            btcpay_conversion_rate = self.action_get_conversion_rate()
            amount_sats = round((float(pos_payment_obj.get('amount')) / float(btcpay_conversion_rate)) * 100000000, 1) #conversion to satoshis and rounding to one decimal
            invoiced_info = {'conversion_rate': btcpay_conversion_rate,
                             'invoiced_sat_amount': amount_sats
                             }
            return invoiced_info #return dictionary with results of both functions
        except Exception as e:
            raise UserError(_("Get Millisat amount: %s", e.args))

    def test_btcpay_server_connection(self): #test connection to btcpayserver eg are server_url, and api_key correct
        try:
            server_url = self.server_url + "/api/v1/api-keys/current"
            headers = {"Authorization": "Token %s" % (self.api_key)}
            response = requests.request(method="GET", url=server_url, headers=headers)
            is_success = True if response.status_code == 200 else False
            return is_success #returns boolean
        except Exception as e:
            raise UserError(_("Test Connection Error: %s", e.args))

    def action_test_connection(self): # turns test_btcpay_server_connection into a message for user
        is_success = self.test_btcpay_server_connection()
        type = (
            "success"
            if is_success
            else "danger"
        )
        messages = (
            "Everything seems properly set up!"
            if is_success
            else "Server credential is wrong. Please check credential."
        )
        title = _("Connection Testing")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": messages,
                "sticky": False,
                "type": type
            },
        }

    def action_activate(self): #activates the btcpay server instance to be the currently used credentials and
        is_success = self.test_btcpay_server_connection() #tests connection
        if is_success:
            self.conversion_rate_source = self.action_get_conversion_rate_source() #gets conversion rate source for reference
            self.state = 'active'
            # Auto create Account Journal and POS Payment Method at the first Activate
            journal = self.env['account.journal'].search(
                [("use_btcpay_server", "=", True), ("type", "=", "bank"), ('company_id', '=', self.env.company.id)],
                limit=1) #looks for journal in existence
            if not journal: #if journal not found
                journal = self.env['account.journal'].search(
                    [("type", "=", "bank"), ('company_id', '=', self.env.company.id)], limit=1)
                new_btcpay_server_journal = journal.copy() #create journal by copying bank journal
                new_btcpay_server_journal.write({
                    'name': 'BTCPay Server',
                    'use_btcpay_server': True,
                    'code': 'BTCP',
                    'btcpay_server_instance_id': self.id
                })
                new_btcpay_server_pos_payment_method = self.env['pos.payment.method'].create({
                    'name': 'BTCPay Server (Lightning)',
                    'company_id': self.env.company.id,
                    'journal_id': new_btcpay_server_journal.id
                }) #creates journal for lightning payments

    def action_deactivate(self):
        self.state = 'inactive'

    def action_create_invoice_lightning(self, pos_payment_obj): #creates lightning invoice
        try:
            invoiced_info = self.get_amount_sats(pos_payment_obj) # gets the invoiced satoshi amount and conversion rate from get_amount_sats function
            amount_millisats = invoiced_info['invoiced_sat_amount'] * 1000 #converts sats to millisats as required by btcpayserver
            server_url = self.server_url + "/api/v1/stores/" + self.store_id + "/lightning/BTC/invoices"
            headers = {"Authorization": "Token %s" % (self.api_key), "Content-Type": "application/json"}
            lightning_expiration_minutes = self.expiration_minutes * 60 #conversion of expiration time from min to sec for submission to btcpay server
            payload = {
                "amount": amount_millisats,
                "description": f"{self.btcpay_company_name} {pos_payment_obj.get('order_name')}", #desciption for customer - company name and order name
                "expiry": lightning_expiration_minutes,
            }
            response = requests.post(server_url, data=json.dumps(payload), headers=headers)
            response_json = response.json()
            result = response_json if response.status_code == 200 else None
            result.update(invoiced_info) #attach invoiced info (sat amount and conversion rate to API response
            return result #returns merged resuls
        except Exception as e:
            raise UserError(_("Create BTCPay Lightning Invoice: %s", e.args))


    def action_check_lightning_invoice(self, lightning_invoice_id): #checks status of lightning invoices, only
        try:
            server_url = self.server_url + "/api/v1/stores/" + self.store_id + "/lightning/BTC/invoices/" + lightning_invoice_id
            headers = {"Authorization": "Token %s" % (self.api_key), "Content-Type": "application/json"}
            response = requests.request(method="GET", url=server_url, headers=headers)
            response_json = response.json()
            result = response_json if response.status_code == 200 else None
            return result
        except Exception as e:
            raise UserError(_("Check BTCPay Lightning Invoice: %s", lightning_invoice_id, e.args))
