import os
import sys

import pytest

# Ensure the repository root is on the path when tests are run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from number_utils import words_to_numbers, numbers_to_words, extract_reservation_number_from_text


def test_words_to_numbers_and_extraction():
    cases = [
        (
            "reservation number one two three four five six",
            "reservation number 1 2 3 4 5 6",
            "123456",
        ),
        (
            "seven eight nine zero one two",
            "7 8 9 0 1 2",
            "789012",
        ),
        (
            "my number is five five five one two three four",
            "my number is 5 5 5 1 2 3 4",
            "555123",
        ),
        (
            "reservation 123456",
            "reservation 123456",
            "123456",
        ),
    ]
    for text, converted, expected in cases:
        assert words_to_numbers(text) == converted
        assert extract_reservation_number_from_text(text) == expected


def test_numbers_to_words():
    cases = [
        (
            "I found your reservation for Jane Smith on 2025-06-11 at 8:00 PM for 2 people. Reservation number: 789012. Total bill: $89.00.",
            "I found your reservation for Jane Smith on 2025-06-11 at 8:00 PM for two people. Reservation number: seven eight nine zero one two. Total bill: $89.00.",
        ),
        (
            "Your reservation number is 123456.",
            "Your reservation number is one two three four five six.",
        ),
        (
            "Call us at 555-1234 for assistance.",
            "Call us at 555-1234 for assistance.",
        ),
    ]
    for text, expected in cases:
        assert numbers_to_words(text) == expected

