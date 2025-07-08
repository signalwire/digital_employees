"""
Shared utilities for restaurant skills
"""

import re
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

def normalize_phone_number(phone_number: Optional[str], caller_id: Optional[str] = None) -> Optional[str]:
    """
    Normalize phone number to E.164 format (+1XXXXXXXXXX)
    
    Args:
        phone_number: Phone number provided by user (can be None)
        caller_id: Caller ID from the call (fallback if phone_number is None)
        
    Returns:
        Normalized phone number in E.164 format
    """
    # If no phone number provided, use caller ID
    if not phone_number and caller_id:
        phone_number = caller_id
        print(f"🔄 Using caller ID as phone number: {caller_id}")
    
    if not phone_number:
        return None
    
    # If already in E.164 format, return as-is
    if phone_number.startswith('+1') and len(phone_number) == 12:
        return phone_number
    
    # Extract only digits
    digits = re.sub(r'\D', '', phone_number)
    
    # Handle different digit lengths
    if len(digits) == 10:
        # 10 digits: add +1 prefix
        normalized = f"+1{digits}"
        print(f"🔄 Normalized 10-digit number {digits} to {normalized}")
        return normalized
    elif len(digits) == 11 and digits.startswith('1'):
        # 11 digits starting with 1: add + prefix
        normalized = f"+{digits}"
        print(f"🔄 Normalized 11-digit number {digits} to {normalized}")
        return normalized
    elif len(digits) == 7:
        # 7 digits: assume local number, add area code 555 and +1
        normalized = f"+1555{digits}"
        print(f"🔄 Normalized 7-digit number {digits} to {normalized} (added 555 area code)")
        return normalized
    else:
        # Return original if we can't normalize
        print(f"⚠️  Could not normalize phone number: {phone_number} (digits: {digits})")
        return phone_number

def extract_phone_from_conversation(call_log: List[Dict[str, Any]]) -> Optional[str]:
    """
    Extract phone number from conversation using spoken number conversion
    
    Args:
        call_log: List of conversation entries
        
    Returns:
        Extracted phone number in E.164 format or None
    """
    if not call_log:
        return None
    
    for entry in call_log:
        if entry.get('role') == 'user' and entry.get('content'):
            content = entry['content'].lower()
            
            # Look for phone number mentions
            if any(phrase in content for phrase in ['phone number', 'my number', 'use number', 'different number']):
                # Convert spoken numbers to digits
                number_words = {
                    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
                    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
                }
                
                # Use word boundaries to avoid replacing parts of other words
                phone_part = content
                for word, digit in number_words.items():
                    phone_part = re.sub(r'\b' + word + r'\b', digit, phone_part)
                
                # Extract digits and format as phone number
                phone_digits = re.findall(r'\d', phone_part)
                if len(phone_digits) >= 7:  # At least 7 digits for a phone number
                    if len(phone_digits) >= 10:
                        # Take first 10 digits
                        extracted_phone = ''.join(phone_digits[:10])
                        normalized = normalize_phone_number(extracted_phone)
                        print(f"🔄 Extracted phone number from conversation: {normalized}")
                        return normalized
                    else:
                        # Take available digits and normalize
                        extracted_phone = ''.join(phone_digits)
                        normalized = normalize_phone_number(extracted_phone)
                        print(f"🔄 Extracted partial phone number from conversation: {normalized}")
                        return normalized
    
    return None

def validate_date_format(date_str: str) -> bool:
    """
    Validate date string is in YYYY-MM-DD format
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not date_str:
        return False
    
    try:
        from datetime import datetime
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_time_format(time_str: str) -> bool:
    """
    Validate time string is in HH:MM format
    
    Args:
        time_str: Time string to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not time_str:
        return False
    
    try:
        from datetime import datetime
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False

def validate_party_size(party_size: int) -> bool:
    """
    Validate party size is within reasonable limits
    
    Args:
        party_size: Number of people in party
        
    Returns:
        True if valid, False otherwise
    """
    return isinstance(party_size, int) and 1 <= party_size <= 20

def validate_business_hours(time_str: str) -> bool:
    """
    Validate time is within business hours (8 AM - 10 PM)
    
    Args:
        time_str: Time string in HH:MM format
        
    Returns:
        True if within business hours, False otherwise
    """
    if not validate_time_format(time_str):
        return False
    
    try:
        from datetime import datetime
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        # Business hours: 8:00 AM to 10:00 PM
        return time_obj >= datetime.strptime('08:00', '%H:%M').time() and \
               time_obj <= datetime.strptime('22:00', '%H:%M').time()
    except ValueError:
        return False

def validate_function_args(args: Dict[str, Any], required_fields: list, optional_fields: list = None) -> Dict[str, Any]:
    """
    Validate function arguments and provide defaults
    
    Args:
        args: Function arguments to validate
        required_fields: List of required field names
        optional_fields: List of optional field names with defaults
        
    Returns:
        Dict with validated and normalized arguments
        
    Raises:
        ValueError: If required fields are missing
    """
    if not args:
        args = {}
        
    # Check required fields
    missing_fields = [field for field in required_fields if not args.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Add optional fields with defaults
    if optional_fields:
        for field_def in optional_fields:
            if isinstance(field_def, tuple):
                field_name, default_value = field_def
                if field_name not in args:
                    args[field_name] = default_value
    
    return args

def extract_call_context(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract consistent call context from raw_data
    
    Args:
        raw_data: Raw SWAIG request data
        
    Returns:
        Dict with normalized call context
    """
    context = {
        'call_id': None,
        'caller_phone': None,
        'ai_session_id': None,
        'call_log': [],
        'meta_data': {}
    }
    
    if not raw_data or not isinstance(raw_data, dict):
        return context
    
    # Extract call_id
    context['call_id'] = raw_data.get('call_id')
    
    # Extract caller phone from multiple possible locations
    context['caller_phone'] = (
        raw_data.get('caller_id_num') or 
        raw_data.get('caller_id_number') or
        raw_data.get('from') or
        raw_data.get('from_number')
    )
    
    # Check global_data for additional phone info
    global_data = raw_data.get('global_data', {})
    if not context['caller_phone'] and global_data:
        context['caller_phone'] = (
            global_data.get('caller_id_number') or
            global_data.get('caller_id_num')
        )
    
    # Extract other context
    context['ai_session_id'] = raw_data.get('ai_session_id', 'default')
    context['call_log'] = raw_data.get('call_log', [])
    context['meta_data'] = raw_data.get('meta_data', {})
    
    return context

def create_error_response(message: str, error_type: str = "general", **kwargs) -> 'SwaigFunctionResult':
    """
    Create a standardized error response
    
    Args:
        message: Error message for the user
        error_type: Type of error for logging/debugging
        **kwargs: Additional metadata to include
        
    Returns:
        SwaigFunctionResult with error information
    """
    try:
        from signalwire_agents.core.function_result import SwaigFunctionResult
        
        result = SwaigFunctionResult(message)
        
        metadata = {
            'error': True,
            'error_type': error_type,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        result.set_metadata(metadata)
        return result
        
    except ImportError:
        # Fallback if SwaigFunctionResult not available
        return {
            'success': False,
            'message': message,
            'error_type': error_type,
            **kwargs
        }

def log_function_call(function_name: str, args: Dict[str, Any], call_context: Dict[str, Any], 
                     result: Any = None, error: Exception = None):
    """
    Log function calls for debugging and monitoring
    
    Args:
        function_name: Name of the function being called
        args: Function arguments
        call_context: Call context from extract_call_context
        result: Function result (optional)
        error: Exception if function failed (optional)
    """
    call_id = call_context.get('call_id', 'unknown')
    
    print(f"🔧 FUNCTION CALL: {function_name}")
    print(f"   Call ID: {call_id}")
    print(f"   Args: {args}")
    
    if error:
        print(f"   ❌ ERROR: {error}")
        import traceback
        traceback.print_exc()
    elif result:
        print(f"   ✅ SUCCESS: {type(result).__name__}")
    
    print(f"   Timestamp: {datetime.now()}")

def normalize_phone_number(phone_number: str, default_country_code: str = "+1") -> Optional[str]:
    """
    Normalize phone number to E.164 format
    
    Args:
        phone_number: Phone number to normalize
        default_country_code: Default country code to add
        
    Returns:
        Normalized phone number or None if invalid
    """
    if not phone_number:
        return None
    
    import re
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone_number)
    
    # Handle different formats
    if len(digits) == 10:
        # US number without country code
        return f"{default_country_code}{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        # US number with country code
        return f"+{digits}"
    elif len(digits) >= 10:
        # International number
        return f"+{digits}"
    
    return None

def safe_get_from_dict(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Safely get value from nested dictionary using dot notation
    
    Args:
        data: Dictionary to search
        path: Dot-separated path (e.g., "user.profile.name")
        default: Default value if path not found
        
    Returns:
        Value at path or default
    """
    try:
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
                
        return value
        
    except (AttributeError, TypeError, KeyError):
        return default

class SignalWireAgentError(Exception):
    """Custom exception for SignalWire agent errors"""
    
    def __init__(self, message: str, error_type: str = "general", context: Dict[str, Any] = None):
        super().__init__(message)
        self.error_type = error_type
        self.context = context or {}
        self.timestamp = datetime.now()

def handle_function_exceptions(func):
    """
    Decorator to handle exceptions in SignalWire function handlers
    
    Usage:
        @handle_function_exceptions
        def my_function_handler(self, args, raw_data):
            ...
    """
    def wrapper(self, args, raw_data):
        try:
            call_context = extract_call_context(raw_data)
            log_function_call(func.__name__, args, call_context)
            
            result = func(self, args, raw_data)
            
            log_function_call(func.__name__, args, call_context, result=result)
            return result
            
        except Exception as e:
            call_context = extract_call_context(raw_data)
            log_function_call(func.__name__, args, call_context, error=e)
            
            error_message = f"I'm sorry, there was an error processing your request. Please try again."
            return create_error_response(
                error_message,
                error_type=type(e).__name__,
                function=func.__name__,
                call_id=call_context.get('call_id')
            )
    
    return wrapper 
