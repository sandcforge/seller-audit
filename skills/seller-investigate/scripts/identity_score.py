#!/usr/bin/env python3
"""
Identity Score Calculator

Scoring system for Google Search identity verification.
Compares applicant data with found profile to determine match strength.

Scoring rules:
- Full name + exact city match: 3 points
- Full name + same state (not city): 2 points
- Email visible and matches: 3 points
- Username matches: 2 points
- Phone number matches: 3 points
- Company name matches: 2 points
- Same category: 1 point

Thresholds: >=4 strong, 2-3 weak, <=1 none
"""

import json
import sys
import argparse
from typing import Dict, Any, List, Tuple


def normalize_string(s: str) -> str:
    """Normalize string for comparison."""
    if not s:
        return ''
    return s.lower().strip()


def extract_city_state(location: str) -> Tuple[str, str]:
    """Extract city and state from location string."""
    if not location:
        return '', ''

    # Try to split by comma
    parts = location.split(',')

    if len(parts) == 2:
        city = normalize_string(parts[0])
        state = normalize_string(parts[1])
        return city, state
    elif len(parts) == 1:
        # Try to extract state (last 2 chars if uppercase)
        parts = location.strip().split()
        if parts and len(parts[-1]) == 2:
            state = normalize_string(parts[-1])
            city = normalize_string(' '.join(parts[:-1]))
            return city, state
        return normalize_string(location), ''

    return normalize_string(location), ''


def score_full_name(applicant_name: str, found_name: str) -> int:
    """
    Score full name match. 0, 2, or 3 points.
    Returns: (points, matched_signal)
    """
    app_name = normalize_string(applicant_name)
    found = normalize_string(found_name)

    if not app_name or not found:
        return 0, None

    if app_name == found:
        return 3, 'full_name_exact'

    # Check if all words match (order-independent)
    app_words = set(app_name.split())
    found_words = set(found.split())

    if app_words and found_words and app_words == found_words:
        return 3, 'full_name_exact'

    # Check partial match (at least first and last name)
    app_parts = app_name.split()
    found_parts = found.split()

    if len(app_parts) >= 2 and len(found_parts) >= 2:
        # Match first and last
        if (app_parts[0] == found_parts[0] and app_parts[-1] == found_parts[-1]):
            return 2, 'full_name_first_last'

    return 0, None


def score_location(app_location: str, found_location: str) -> int:
    """
    Score location match. 0, 2, or 3 points.
    Returns: (points, matched_signal)
    """
    if not app_location or not found_location:
        return 0, None

    app_city, app_state = extract_city_state(app_location)
    found_city, found_state = extract_city_state(found_location)

    # Exact city match (including state)
    if app_city and found_city and app_city == found_city:
        if app_state and found_state and app_state == found_state:
            return 3, 'full_name+exact_city'
        elif app_state and found_state and app_state == found_state:
            return 3, 'full_name+exact_city'

    # State match (not city)
    if app_state and found_state and app_state == found_state:
        return 2, 'full_name+same_state'

    # Partial city match (first word)
    if app_city and found_city:
        app_city_first = app_city.split()[0] if app_city else ''
        found_city_first = found_city.split()[0] if found_city else ''
        if app_city_first and found_city_first and app_city_first == found_city_first:
            return 2, 'partial_city_match'

    return 0, None


def score_email(app_email: str, found_email: str) -> int:
    """Score email match. 0 or 3 points."""
    if not app_email or not found_email:
        return 0, None

    app_email = normalize_string(app_email)
    found_email = normalize_string(found_email)

    if app_email == found_email:
        return 3, 'email_matches'

    return 0, None


def score_username(app_username: str, found_username: str) -> int:
    """Score username match. 0 or 2 points."""
    if not app_username or not found_username:
        return 0, None

    app_user = normalize_string(app_username)
    found_user = normalize_string(found_username)

    if app_user == found_user:
        return 2, 'username_matches'

    return 0, None


def score_phone(app_phone: str, found_phone: str) -> int:
    """Score phone match. 0 or 3 points."""
    if not app_phone or not found_phone:
        return 0, None

    # Remove common formatting
    def clean_phone(phone: str) -> str:
        return ''.join(c for c in phone if c.isdigit())

    app_clean = clean_phone(app_phone)
    found_clean = clean_phone(found_phone)

    if app_clean and found_clean and app_clean == found_clean:
        return 3, 'phone_matches'

    return 0, None


def score_company(app_company: str, found_company: str) -> int:
    """Score company name match. 0 or 2 points."""
    if not app_company or not found_company:
        return 0, None

    app_comp = normalize_string(app_company)
    found_comp = normalize_string(found_company)

    if app_comp == found_comp:
        return 2, 'company_matches'

    return 0, None


def score_category(app_category: str, found_category: str) -> int:
    """Score category match. 0 or 1 point."""
    if not app_category or not found_category:
        return 0, None

    app_cat = normalize_string(app_category)
    found_cat = normalize_string(found_category)

    if app_cat == found_cat:
        return 1, 'category_matches'

    return 0, None


def calculate_identity_score(applicant: Dict[str, Any], found: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate identity match score.

    Returns score object with total, match_level, signals, and recommendation.
    """
    total_score = 0
    signals_matched = []
    signals_checked = []

    # Full name check
    signals_checked.append('full_name')
    points, signal = score_full_name(
        applicant.get('full_name', ''),
        found.get('name', '')
    )
    total_score += points
    if signal:
        signals_matched.append(signal)

    # Location check
    signals_checked.append('location')
    points, signal = score_location(
        applicant.get('location', ''),
        found.get('location', '')
    )
    total_score += points
    if signal:
        signals_matched.append(signal)

    # Email check
    signals_checked.append('email')
    points, signal = score_email(
        applicant.get('email', ''),
        found.get('email', '')
    )
    total_score += points
    if signal:
        signals_matched.append(signal)

    # Username check
    signals_checked.append('username')
    points, signal = score_username(
        applicant.get('username', ''),
        found.get('username', '')
    )
    total_score += points
    if signal:
        signals_matched.append(signal)

    # Phone check
    signals_checked.append('phone')
    points, signal = score_phone(
        applicant.get('phone', ''),
        found.get('phone', '')
    )
    total_score += points
    if signal:
        signals_matched.append(signal)

    # Company check
    signals_checked.append('company')
    points, signal = score_company(
        applicant.get('company', ''),
        found.get('company', '')
    )
    total_score += points
    if signal:
        signals_matched.append(signal)

    # Category check
    signals_checked.append('category')
    points, signal = score_category(
        applicant.get('category', ''),
        found.get('category', '')
    )
    total_score += points
    if signal:
        signals_matched.append(signal)

    # Determine match level
    if total_score >= 4:
        match_level = 'strong'
        recommendation = 'Can attribute this profile to the applicant'
    elif 2 <= total_score < 4:
        match_level = 'weak'
        recommendation = 'Unconfirmed match; use with caution'
    else:
        match_level = 'none'
        recommendation = 'Cannot confirm; discard this profile'

    return {
        'total_score': total_score,
        'match_level': match_level,
        'signals_matched': signals_matched,
        'signals_checked': signals_checked,
        'recommendation': recommendation
    }


def main():
    parser = argparse.ArgumentParser(
        description='Calculate identity match score for Google Search verification'
    )
    parser.add_argument('--input', help='Input JSON file')

    args = parser.parse_args()

    # Read input
    if args.input:
        with open(args.input, 'r') as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    # Single item or batch
    if isinstance(data, list):
        results = []
        for item in data:
            applicant = item.get('applicant', {})
            found = item.get('found_profile', {})
            score_result = calculate_identity_score(applicant, found)
            results.append(score_result)
        print(json.dumps(results, indent=2))
    else:
        applicant = data.get('applicant', {})
        found = data.get('found_profile', {})
        result = calculate_identity_score(applicant, found)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
