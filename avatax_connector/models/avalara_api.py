# -*- coding: utf-8 -*-
"""
Avalara API Integration
=======================
This module provides the BaseAddress class and AvaTaxService for address validation.
"""

import logging

_logger = logging.getLogger(__name__)


class BaseAddress:
    """
    BaseAddress class for creating address objects compatible with AvaTax API.
    
    This class creates a BaseAddress object that can be used with the AvaTax
    address validation service.
    """
    
    def __init__(self, addSvc, Line1=None, Line2=None, City=None, 
                 PostalCode=None, Region=None, Country=None, AddressCode=None):
        """
        Initialize BaseAddress object.
        
        :param addSvc: AvaTax address service factory
        :param Line1: Street address line 1
        :param Line2: Street address line 2 (apartment, suite, etc.)
        :param City: City name
        :param PostalCode: ZIP/Postal code
        :param Region: State/Province code (2-letter code)
        :param Country: Country code (2-letter ISO code)
        :param AddressCode: Address code identifier (0 for origin, 1 for destination)
        """
        self.data = addSvc.factory.create('BaseAddress')
        self.data.TaxRegionId = 0
        self.data.Line1 = Line1
        self.data.Line2 = Line2
        self.data.City = City
        self.data.PostalCode = PostalCode
        self.data.Region = Region
        self.data.Country = Country
        self.data.AddressCode = AddressCode
