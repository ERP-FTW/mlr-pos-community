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

    def action_get_stores(self):  # gets store IDs on nodeless server
        try:
            server_url = self.server_url + "/api/v1/store"
            headers = {"Authorization": "Bearer %s" % (self.api_key), "Content-Type": "application/json",
                       "Accept": "application/json"}
            response = requests.request(method="GET", url=server_url, headers=headers)
            response_json = response.json()
            result = response_json['data'] if response.status_code == 200 else None
            return result
        except Exception as e:
            raise UserError(_("Get Conversion Rate Source: %s", e.args))


    def test_nodeless_server_connection(self): #test connection to nodelessserver eg are server_url, and api_key correct
        try:
            server_url = self.server_url + "/api/v1/status"
            headers = {"Authorization": "Bearer %s" % (self.api_key), "Content-Type": "application/json", "Accept": "application/json"}
            response = requests.request(method="GET", url=server_url, headers=headers)
            is_success = True if response.status_code == 200 else False
            return is_success #returns boolean
        except Exception as e:
            raise UserError(_("Test Connection Error: %s", e.args))

    def action_test_connection(self): # turns test_btcpay_server_connection into a message for user
        is_success = self.test_nodeless_server_connection()
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
        is_success = self.test_nodeless_server_connection() #tests connection
        if is_success:
            self.conversion_rate_source = self.action_get_stores() #gets conversion rate source for reference
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

    def action_create_invoice_lightning(self, pos_payment_obj):  # creates lightning invoice
        try:
            server_url = self.server_url + "/api/v1/store/" + self.store_id + "/invoice"
            headers = {"Authorization": "Bearer %s" % (self.api_key), "Content-Type": "application/json",
                       "Accept": "application/json"}
            payload = {
                "amount": pos_payment_obj.get('amount'),
                "currency": "USD",
            }
            response = requests.post(server_url, data=json.dumps(payload), headers=headers)
            response_json = response.json()
            result = response_json if response.status_code == 201 else None
            conversion_rate = round(pos_payment_obj.get('amount') / (result['data'].get('satsAmount') / 100000000), 2)
            result.update({'invoiced_sat_amount': result['data'].get('satsAmount'),
                           'conversion_rate': conversion_rate})  # attach invoiced info (sat amount and conversion rate to API response
            return result  # returns merged resuls
        except Exception as e:
            _logger.info('triggered action create invoice lightning - exception')
            raise UserError(_("Create nodeless Lightning Invoice: %s", e.args))

    def action_check_lightning_invoice(self, lightning_invoice_id):  # checks status of lightning invoices, only
        try:
            server_url = self.server_url + "/api/v1/store/" + self.store_id + "/invoice/" + lightning_invoice_id + "/status"
            headers = {"Authorization": "Bearer %s" % (self.api_key), "Content-Type": "application/json",
                       "Accept": "application/json"}
            response = requests.request(method="GET", url=server_url, headers=headers)
            response_json = response.json()
            result = response_json if response.status_code == 200 else None
            _logger.info(response.status_code)
            _logger.info(response_json)
            return result
        except Exception as e:
            raise UserError(_("Check nodeless Lightning Invoice: %s", lightning_invoice_id, e.args))
