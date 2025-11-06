# -*- coding: utf-8 -*-
"""
Partner Address Validation Enhancement
======================================
This module enhances the res.partner model to properly validate and format
addresses before sending them to AvaTax, ensuring better compatibility with
AvaTax address validation requirements.
"""

import logging
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from .avalara_api import BaseAddress

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """
    Enhanced res.partner model with improved AvaTax address validation.
    
    This module extends the res.partner model to provide better address
    validation by properly formatting and normalizing address data before
    sending it to AvaTax, handling edge cases and missing fields gracefully.
    """
    _inherit = 'res.partner'

    def _normalize_address_field(self, value):
        """
        Normalize address field values by cleaning whitespace and handling None/empty strings.
        
        :param value: The address field value to normalize
        :return: Normalized string or None
        """
        if not value:
            return None
        if isinstance(value, str):
            # Strip leading/trailing whitespace and collapse multiple spaces
            normalized = re.sub(r'\s+', ' ', value.strip())
            return normalized if normalized else None
        return str(value).strip() if value else None

    def _normalize_postal_code(self, postal_code):
        """
        Normalize postal code by removing spaces and hyphens.
        
        US ZIP codes should be 5 digits or 5+4 format (ZIP+4).
        Canadian postal codes should be formatted as A1A 1A1.
        
        :param postal_code: The postal code to normalize
        :return: Normalized postal code string or None
        """
        if not postal_code:
            return None
        
        postal_code = str(postal_code).strip().upper()
        # Remove spaces and hyphens for US ZIP codes
        postal_code = re.sub(r'[\s-]', '', postal_code)
        
        # For US ZIP codes, ensure we have at least 5 digits
        if postal_code and postal_code.isdigit():
            # If it's a ZIP+4 format (9 digits), format it properly
            if len(postal_code) == 9:
                return '%s-%s' % (postal_code[:5], postal_code[5:])
            elif len(postal_code) >= 5:
                return postal_code[:5]
        
        return postal_code if postal_code else None

    def _get_state_code(self, state_id):
        """
        Get state code from state_id.
        
        :param state_id: State record ID or tuple (id, name)
        :return: 2-letter state code or None
        """
        if not state_id:
            return None
        
        # Handle tuple format (id, name) from read()
        if isinstance(state_id, (list, tuple)):
            state_id = state_id[0] if state_id else None
        
        if not state_id:
            return None
        
        try:
            state = self.env['res.country.state'].browse(state_id)
            if state.exists() and state.code:
                return state.code.upper().strip()
        except Exception as e:
            _logger.warning("Error getting state code for state_id %s: %s", state_id, e)
        
        return None

    def _get_country_code(self, country_id):
        """
        Get country code from country_id.
        
        :param country_id: Country record ID or tuple (id, name)
        :return: 2-letter ISO country code or None
        """
        if not country_id:
            return None
        
        # Handle tuple format (id, name) from read()
        if isinstance(country_id, (list, tuple)):
            country_id = country_id[0] if country_id else None
        
        if not country_id:
            return None
        
        try:
            country = self.env['res.country'].browse(country_id)
            if country.exists() and country.code:
                return country.code.upper().strip()
        except Exception as e:
            _logger.warning("Error getting country code for country_id %s: %s", country_id, e)
        
        return None

    def _prepare_address_for_validation(self, address):
        """
        Prepare and normalize address data before sending to AvaTax.
        
        This method ensures that address fields are properly formatted,
        missing required fields are handled gracefully, and the address
        is in the correct format for AvaTax validation.
        
        :param address: Dictionary containing address fields
        :return: Dictionary with normalized address fields
        """
        normalized_address = {}
        
        # Normalize street address line 1
        street = self._normalize_address_field(address.get('street'))
        normalized_address['street'] = street
        
        # Normalize street address line 2
        street2 = self._normalize_address_field(address.get('street2'))
        normalized_address['street2'] = street2
        
        # Normalize city
        city = self._normalize_address_field(address.get('city'))
        normalized_address['city'] = city
        
        # Normalize postal code
        zip_code = self._normalize_postal_code(address.get('zip'))
        normalized_address['zip'] = zip_code
        
        # Get state code
        state_id = address.get('state_id')
        state_code = None
        if state_id:
            state_code = self._get_state_code(state_id)
        normalized_address['state_code'] = state_code
        
        # Get country code
        country_id = address.get('country_id')
        country_code = None
        if country_id:
            country_code = self._get_country_code(country_id)
        normalized_address['country_code'] = country_code
        
        # Store original IDs for later use
        normalized_address['state_id'] = state_id
        normalized_address['country_id'] = country_id
        
        # Log normalized address for debugging
        _logger.debug("Normalized address: %s", normalized_address)
        
        return normalized_address

    def _validate_address(self, address, avatax_config=False):
        """
        Enhanced address validation method that properly formats and validates
        address data before sending to AvaTax.
        
        This method improves upon the original implementation by:
        1. Normalizing and cleaning address fields before validation
        2. Properly handling missing or malformed address components
        3. Ensuring state and country codes are correctly formatted
        4. Providing better error messages and logging
        
        :param address: Dictionary containing address fields (street, street2, city, zip, state_id, country_id)
        :param avatax_config: Optional AvaTax configuration object
        :return: Validated address object from AvaTax
        :raises: UserError if validation fails or configuration is missing
        """
        # Get AvaTax configuration if not provided
        if not avatax_config:
            company = self.company_id or self.env.user.company_id
            if hasattr(company, 'get_avatax_config_company'):
                avatax_config = company.get_avatax_config_company()
        
        if not avatax_config:
            raise UserError(_(
                "AvaTax module has not been configured. "
                "Please configure AvaTax in Accounting >> Configuration >> AvaTax >> AvaTax API."
            ))
        
        # Validate AvaTax configuration
        if not avatax_config.account_number or not avatax_config.license_key:
            raise UserError(_(
                "AvaTax credentials are missing. "
                "Please configure your AvaTax account number and license key."
            ))
        
        if not avatax_config.service_url or not avatax_config.request_timeout:
            raise UserError(_(
                "AvaTax service configuration is incomplete. "
                "Please configure the service URL and request timeout."
            ))
        
        try:
            # Import AvaTaxService here to avoid circular imports
            try:
                from .avalara_api import AvaTaxService
            except ImportError:
                from odoo.addons.avatax_connector.models.avalara_api import AvaTaxService
            # Create AvaTax service instance
            avapoint = AvaTaxService(
                avatax_config.account_number,
                avatax_config.license_key,
                avatax_config.service_url,
                avatax_config.request_timeout,
                avatax_config.logging
            )
            addSvc = avapoint.create_address_service().addressSvc
            
            # Prepare and normalize address data
            normalized_address = self._prepare_address_for_validation(address)
            
            # Create BaseAddress object with normalized data
            # Use None instead of empty strings for optional fields
            baseaddress = BaseAddress(
                addSvc,
                Line1=normalized_address.get('street') or None,
                Line2=normalized_address.get('street2') or None,
                City=normalized_address.get('city') or None,
                PostalCode=normalized_address.get('zip') or None,
                Region=normalized_address.get('state_code') or None,
                Country=normalized_address.get('country_code') or None,
                AddressCode=0
            ).data
            
            # Determine text case preference
            textcase = 'Upper' if avatax_config.result_in_uppercase else 'Default'
            
            # Validate address with AvaTax
            _logger.info(
                "Validating address with AvaTax: %s, %s, %s %s",
                normalized_address.get('street'),
                normalized_address.get('city'),
                normalized_address.get('state_code'),
                normalized_address.get('zip')
            )
            
            result = avapoint.validate_address(baseaddress, textcase)
            
            # Check if validation was successful
            if not result or not hasattr(result, 'ValidAddresses'):
                raise UserError(_(
                    "AvaTax address validation returned an invalid response. "
                    "Please check your address and try again."
                ))
            
            if not result.ValidAddresses or len(result.ValidAddresses) == 0:
                # Check for error messages in the result
                error_message = _("Address validation failed.")
                if hasattr(result, 'Messages') and result.Messages:
                    messages = []
                    for msg in result.Messages:
                        if hasattr(msg, 'Summary'):
                            messages.append(msg.Summary)
                    if messages:
                        error_message = _("Address validation failed: %s") % '; '.join(messages)
                
                _logger.warning(
                    "AvaTax address validation failed for address: %s",
                    normalized_address
                )
                raise ValidationError(error_message)
            
            # Get the first valid address
            valid_address = result.ValidAddresses[0][0]
            
            _logger.info(
                "Address validation successful. Validated address: %s, %s, %s %s",
                valid_address.Line1 if hasattr(valid_address, 'Line1') else '',
                valid_address.City if hasattr(valid_address, 'City') else '',
                valid_address.Region if hasattr(valid_address, 'Region') else '',
                valid_address.PostalCode if hasattr(valid_address, 'PostalCode') else ''
            )
            
            return valid_address
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except UserError:
            # Re-raise user errors as-is
            raise
        except Exception as e:
            _logger.error(
                "Error during AvaTax address validation: %s. Address: %s",
                str(e), address, exc_info=True
            )
            raise UserError(_(
                "An error occurred during address validation: %s\n\n"
                "Please verify your address information and AvaTax configuration."
            ) % str(e))
