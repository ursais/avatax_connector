# -*- coding: utf-8 -*-
{
    'name': 'AvaTax Connector',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'AvaTax integration for Odoo',
    'description': """
        AvaTax Connector Module
        =======================
        
        This module provides integration with Avalara AvaTax for address validation
        and tax calculation.
        
        Features:
        - Address validation using AvaTax API
        - Enhanced address formatting and validation before sending to AvaTax
        - Proper handling of missing or malformed address fields
    """,
    'author': 'Open Source Integrators',
    'website': 'https://www.opensourceintegrators.com',
    'depends': ['base', 'sale', 'account'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
