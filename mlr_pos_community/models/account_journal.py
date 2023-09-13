# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    use_btcpay_server = fields.Boolean('Use BTCPay Server')
    btcpay_server_instance_id = fields.Many2one('btcpay.server.instance', 'BTCPay Server Instance')