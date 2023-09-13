{
    "name": "MI Lightning Rod Point of Sale - Community",
    "summary": "MI Lightning Rod Point of Sale - Community",
    "author": "ERP-FTW and Toan Truong",
    "website": "https://www.milightningrod.com",
    "category": "Point of Sale",
    "version": "1.0",
    "depends": ["point_of_sale", "account", "pos_restaurant"],
    "data": [
        "security/ir.model.access.csv",
        "views/btcpay_server_instance_views.xml",
        "views/account_journal.xml",
        "views/pos_payment.xml",
    ],
    'assets': {
        'point_of_sale.assets': [
            'mlr_pos_community/static/src/js/models.js',
            'mlr_pos_community/static/src/js/ValidatePaymentScreen.js',
            'mlr_pos_community/static/src/js/create_invoice.js',
            'mlr_pos_community/static/src/xml/OrderReceipt.xml',
            'mlr_pos_community/static/src/xml/create_invoice.xml'
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "OPL-1",
}
