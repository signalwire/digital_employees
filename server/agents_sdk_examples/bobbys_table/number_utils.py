#!/usr/bin/env python3
"""
Number conversion utilities for restaurant reservation system.
Handles converting between spoken numbers and digits for better TTS and speech recognition.
"""

import re

def words_to_numbers(text):
    """
    Convert spoken number words to digits.
    
    Args:
        text (str): Text containing spoken numbers
        
    Returns:
        str: Text with number words converted to digits
    """
    # Word to digit mapping (including common variations)
    number_words = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        # Common variations and abbreviations
        'sev': '7', 'oh': '0', 'o': '0'
    }
    
    # Convert text to lowercase for matching
    result = text.lower()
    
    # Replace word numbers with digits (using word boundaries)
    for word, digit in number_words.items():
        result = re.sub(r'\b' + word + r'\b', digit, result)
    
    return result

def is_credit_card_number(text):
    """
    Detect if text contains credit card numbers to avoid extracting them as reservation numbers.
    
    Args:
        text (str): Text to check for credit card patterns
        
    Returns:
        bool: True if text appears to contain a credit card number
    """
    if not text:
        return False
    
    # Remove spaces and non-digits
    digits_only = re.sub(r'\D', '', text)
    
    # Common credit card lengths: 13-19 digits
    if len(digits_only) >= 13 and len(digits_only) <= 19:
        # Check for common credit card prefixes
        if (digits_only.startswith('4') or      # Visa (starts with 4)
            digits_only.startswith('5') or      # Mastercard (starts with 5)
            digits_only.startswith('3') or      # Amex (starts with 3)
            digits_only.startswith('6') or      # Discover (starts with 6)
            digits_only.startswith('2')):       # Mastercard (some start with 2)
            print(f"🔍 Detected credit card number pattern: {text[:4]}****")
            return True
    
    # Check for common test credit card numbers
    test_cards = [
        '4242424242424242',  # Stripe test Visa
        '4000000000000002',  # Stripe test Visa
        '5555555555554444',  # Stripe test Mastercard
        '378282246310005',   # Stripe test Amex
        '6011111111111117'   # Stripe test Discover
    ]
    
    for test_card in test_cards:
        if digits_only == test_card:
            print(f"🔍 Detected test credit card number: {text}")
            return True
    
    return False

def extract_reservation_number_from_text(text, payment_context=False):
    """
    Extract a 6-digit reservation number from text, handling both digits and spoken words.
    Prioritizes the most recent/last occurrence of a 6-digit number.
    Filters out credit card numbers to prevent confusion.
    
    Args:
        text (str): Text that may contain a reservation number
        payment_context (bool): If True, indicates we're in a payment flow and should be more cautious
        
    Returns:
        str or None: 6-digit reservation number if found, None otherwise
    """
    if not text:
        return None
    
    # If we're in a payment context, be much more cautious about extracting reservation numbers
    if payment_context:
        print(f"🔍 Payment context detected - being cautious with number extraction from: {text}")
        
        # In payment context, only extract if there are explicit reservation keywords
        reservation_keywords = ['reservation', 'booking', 'confirmation', 'table']
        has_reservation_keyword = any(keyword in text.lower() for keyword in reservation_keywords)
        
        if not has_reservation_keyword:
            print(f"🔍 No reservation keywords found in payment context - skipping extraction")
            return None
    
    # Check if this text contains a credit card number - if so, skip extraction
    if is_credit_card_number(text):
        print(f"🔍 Skipping credit card number for reservation extraction: {text}")
        return None
        
    # Convert spoken numbers to digits first
    converted_text = words_to_numbers(text)
    
    # Collect all potential reservation numbers with their positions
    candidates = []
    
    # High-priority patterns (in order of priority)
    high_priority_patterns = [
        r'reservation number\s+is\s+(\d{6})',  # "reservation number is 123456"
        r'reservation\s+number\s+(\d{6})',     # "reservation number 123456"
        r'reservation\s+(\d{6})',              # "reservation 123456"
        r'number\s+is\s+(\d{6})',              # "number is 123456"
        r'my\s+number\s+is\s+(\d{6})',         # "my number is 123456"
        r'it\'s\s+(\d{6})',                    # "it's 123456"
    ]
    
    # Check high-priority patterns in converted text
    for priority, pattern in enumerate(high_priority_patterns):
        for match in re.finditer(pattern, converted_text, re.IGNORECASE):
            candidates.append({
                'number': match.group(1),
                'position': match.end(),  # End position for prioritizing later occurrences
                'priority': priority,     # Lower number = higher priority
                'source': 'converted_high_priority',
                'pattern': pattern
            })
    
    # Check high-priority patterns in original text
    for priority, pattern in enumerate(high_priority_patterns):
        for match in re.finditer(pattern, text, re.IGNORECASE):
            candidates.append({
                'number': match.group(1),
                'position': match.end(),
                'priority': priority + 100,  # Lower priority than converted text
                'source': 'original_high_priority',
                'pattern': pattern
            })
    
    # Look for 6-digit sequences at end of text (high priority)
    # But make sure it's not part of a longer number
    end_pattern = r'(?<!\d)(\d{6})\s*$'  # Negative lookbehind to ensure no digit before
    for match in re.finditer(end_pattern, converted_text):
        candidates.append({
            'number': match.group(1),
            'position': match.end(),
            'priority': -1,  # Highest priority
            'source': 'converted_end',
            'pattern': end_pattern
        })
    
    for match in re.finditer(end_pattern, text):
        candidates.append({
            'number': match.group(1),
            'position': match.end(),
            'priority': 50,  # High priority but lower than converted
            'source': 'original_end',
            'pattern': end_pattern
        })
    
    # Look for sequences of 6 digits with spaces (spoken numbers) - higher priority than regular 6-digit sequences
    # This handles "seven eight nine zero one two" -> "7 8 9 0 1 2"
    spaced_digits_pattern = r'(\d(?:\s+\d){5})'  # 6 digits with spaces between them
    for match in re.finditer(spaced_digits_pattern, converted_text):
        # Extract just the digits without spaces
        digits_only = re.sub(r'[^\d]', '', match.group(1))
        if len(digits_only) == 6:
            candidates.append({
                'number': digits_only,
                'position': match.end(),
                'priority': 10,  # Very high priority for spaced spoken numbers
                'source': 'converted_spaced_digits',
                'pattern': spaced_digits_pattern
            })
    
    # Look for any 6-digit sequences (lower priority) - but filter out parts of longer numbers
    for match in re.finditer(r'\b(\d{6})\b', converted_text):
        # Check if this 6-digit sequence is part of a longer number (like a credit card)
        start_pos = match.start()
        end_pos = match.end()
        
        # Look for digits before and after to see if this is part of a longer sequence
        before_text = converted_text[:start_pos]
        after_text = converted_text[end_pos:]
        
        # Check if there are digits immediately before or after (indicating longer number)
        has_digit_before = before_text and before_text[-1].isdigit()
        has_digit_after = after_text and after_text[0].isdigit()
        
        if not has_digit_before and not has_digit_after:
            # This is a standalone 6-digit number, not part of a longer sequence
            candidates.append({
                'number': match.group(1),
                'position': match.end(),
                'priority': 200,
                'source': 'converted_any',
                'pattern': r'\b(\d{6})\b'
            })
    
    for match in re.finditer(r'\b(\d{6})\b', text):
        # Same filtering for original text
        start_pos = match.start()
        end_pos = match.end()
        
        before_text = text[:start_pos]
        after_text = text[end_pos:]
        
        has_digit_before = before_text and before_text[-1].isdigit()
        has_digit_after = after_text and after_text[0].isdigit()
        
        if not has_digit_before and not has_digit_after:
            candidates.append({
                'number': match.group(1),
                'position': match.end(),
                'priority': 300,
                'source': 'original_any',
                'pattern': r'\b(\d{6})\b'
            })
    
    # Look for sequences of exactly 6 consecutive digits in converted text (medium priority)
    # This handles cases like "one two three four five six" -> "1 2 3 4 5 6"
    # But filter out parts of credit card numbers
    digits_only = re.sub(r'[^\d]', '', converted_text)
    if len(digits_only) == 6:  # Only if the entire text converts to exactly 6 digits
        candidates.append({
            'number': digits_only,
            'position': len(converted_text),
            'priority': 180,
            'source': 'converted_consecutive_digits',
            'pattern': 'consecutive_digits'
        })
    
    # Filter out candidates that are parts of credit card numbers
    filtered_candidates = []
    for candidate in candidates:
        # Check if this candidate number appears to be part of a credit card
        # Look for the candidate number in the context of the original text
        candidate_num = candidate['number']
        
        # Check if this number appears as part of a longer sequence that looks like a credit card
        is_part_of_cc = False
        
        # Look for this 6-digit sequence in longer digit sequences
        all_digit_sequences = re.findall(r'\d{10,}', text + ' ' + converted_text)
        for seq in all_digit_sequences:
            if candidate_num in seq and is_credit_card_number(seq):
                print(f"🔍 Filtering out {candidate_num} - part of credit card {seq[:4]}****")
                is_part_of_cc = True
                break
        
        if not is_part_of_cc:
            filtered_candidates.append(candidate)
    
    candidates = filtered_candidates
    
    # Debug logging
    if candidates:
        print(f"🔍 Found {len(candidates)} reservation number candidates:")
        for i, candidate in enumerate(candidates):
            print(f"   {i+1}. {candidate['number']} (priority: {candidate['priority']}, source: {candidate['source']}, position: {candidate['position']})")
    
    # If we have candidates, sort by priority (lower is better) then by position (later is better)
    if candidates:
        # Special handling: if we have candidates with significantly different positions,
        # prioritize the later position (more recent) even if it has slightly lower priority
        if len(candidates) > 1:
            # Find the candidate with the latest position
            latest_position = max(c['position'] for c in candidates)
            earliest_position = min(c['position'] for c in candidates)
            position_difference = latest_position - earliest_position
            
            # If there's a significant position difference (>20 characters), 
            # and we have spaced digits or consecutive digits at the end,
            # prioritize those over earlier high-priority patterns
            if position_difference > 20:
                recent_candidates = [c for c in candidates if c['position'] >= latest_position - 10]
                if any(c['source'] in ['converted_spaced_digits', 'converted_consecutive_digits', 'converted_end'] 
                       for c in recent_candidates):
                    # Sort recent candidates by priority, then by position
                    recent_candidates.sort(key=lambda x: (x['priority'], -x['position']))
                    selected = recent_candidates[0]
                    print(f"🔍 Selected recent candidate: {selected['number']} (source: {selected['source']})")
                    return selected['number']
        
        # Default sorting: priority first, then by position (descending for later positions)
        candidates.sort(key=lambda x: (x['priority'], -x['position']))
        selected = candidates[0]
        print(f"🔍 Selected best candidate: {selected['number']} (source: {selected['source']}, priority: {selected['priority']})")
        return selected['number']
    
    print(f"🔍 No reservation number candidates found in text: '{text}'")
    return None

def numbers_to_words(text):
    """
    Convert digits in text to spoken words for better TTS pronunciation.
    
    Args:
        text (str): Text containing digits
        
    Returns:
        str: Text with digits converted to words
    """
    # Digit to word mapping
    digit_words = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
    }
    
    result = text
    
    # Handle special cases first (preserve formatting for prices, dates, times)
    # Don't convert digits in prices like $42.00
    price_pattern = r'\$\d+\.\d+'
    prices = re.findall(price_pattern, result)
    price_placeholders = {}
    
    for i, price in enumerate(prices):
        placeholder = f"__PRICE_{i}__"
        price_placeholders[placeholder] = price
        result = result.replace(price, placeholder, 1)
    
    # Don't convert digits in dates like 2025-06-11
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    dates = re.findall(date_pattern, result)
    date_placeholders = {}
    
    for i, date in enumerate(dates):
        placeholder = f"__DATE_{i}__"
        date_placeholders[placeholder] = date
        result = result.replace(date, placeholder, 1)
    
    # Don't convert digits in times like 8:00
    time_pattern = r'\d{1,2}:\d{2}'
    times = re.findall(time_pattern, result)
    time_placeholders = {}
    
    for i, time in enumerate(times):
        placeholder = f"__TIME_{i}__"
        time_placeholders[placeholder] = time
        result = result.replace(time, placeholder, 1)
    
    # Convert standalone digits and reservation numbers
    # Convert reservation numbers (6 consecutive digits)
    reservation_pattern = r'\b(\d{6})\b'
    def convert_reservation_number(match):
        number = match.group(1)
        return ' '.join(digit_words[digit] for digit in number)
    
    result = re.sub(reservation_pattern, convert_reservation_number, result)
    
    # Convert other standalone digits
    for digit, word in digit_words.items():
        # Only convert standalone digits (not part of larger numbers)
        result = re.sub(r'\b' + digit + r'\b', word, result)
    
    # Restore preserved patterns
    for placeholder, original in price_placeholders.items():
        result = result.replace(placeholder, original)
    
    for placeholder, original in date_placeholders.items():
        result = result.replace(placeholder, original)
    
    for placeholder, original in time_placeholders.items():
        result = result.replace(placeholder, original)
    
    return result

def format_phone_number_for_speech(phone_number):
    """
    Format a phone number for better TTS pronunciation.
    
    Args:
        phone_number (str): Phone number in various formats
        
    Returns:
        str: Phone number formatted for speech
    """
    if not phone_number:
        return ""
    
    # Remove common formatting
    clean_number = re.sub(r'[^\d]', '', phone_number)
    
    # Format as groups for better pronunciation
    if len(clean_number) == 10:
        # Format as (XXX) XXX-XXXX
        return f"({clean_number[:3]}) {clean_number[3:6]} {clean_number[6:]}"
    elif len(clean_number) == 11 and clean_number.startswith('1'):
        # Format as 1 (XXX) XXX-XXXX
        return f"1 ({clean_number[1:4]}) {clean_number[4:7]} {clean_number[7:]}"
    else:
        # Return as-is if format is unclear
        return phone_number

if __name__ == '__main__':
    # Simple manual example when running this module directly
    sample = "Your reservation number is 123456."
    print(numbers_to_words(sample))
