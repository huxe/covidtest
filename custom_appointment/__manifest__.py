# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Custom Appointment',
    'version': '15.0.1.1.2',
    'category': 'Sale',
    'summary': 'Module for Odoo Reporting',
    'sequence': '4',
    'author': 'Shaikh Huzaifa',
    'maintainer': 'Zeeshan',
    'depends': ['base','web','appointment','website_sale'],
    'demo': [],
    'data': [
        'security/ir.model.access.csv',
        'Data/add_data.xml',
        'main.xml',
        'views/payment_page.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [],

}
