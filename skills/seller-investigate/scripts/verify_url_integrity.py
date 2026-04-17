#!/usr/bin/env python3
"""
URL Integrity Verification

Character-level comparison between original and visited URLs to detect
silent mutations (e.g., "granitestatecoinsandcurrency" → "granitestatecoinscurrency").

Extracts the path/identifier portion and compares character by character.
"""

import json
import sys
import argparse
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse


def extract_identifier(url: str) -> str:
    """
    Extract the meaningful identifier from a URL.
    For stores/profiles, this is the username or store name.
    Examples:
    - ebay.com/str/STORENAME → STORENAME
    - instagram.com/username → username
    - etsy.com/shop/shopname → shopname
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return ''

    domain = parsed.netloc.lower().replace('www.', '')
    path = parsed.path.strip('/')

    if not path:
        return ''

    parts = [p for p in path.split('/') if p]

    # For each platform, extract the relevant identifier
    if 'instagram.com' in domain:
        # Username is first part
        if parts:
            return parts[0]

    elif 'whatnot.com' in domain:
        # Either /user/{username} or /s/{code}
        if len(parts) >= 2 and parts[0] in ['user', 's', 'invite']:
            return parts[1]
        elif len(parts) == 1:
            return parts[0]

    elif 'facebook.com' in domain or domain == 'fb.me':
        # Could be /username, /profile.php?id=123, /marketplace/profile/...
        if parts and parts[0] != 'profile.php':
            return parts[0]
        # For profile.php?id=X, try to extract ID from query
        from urllib.parse import parse_qs
        qs = parse_qs(parsed.query)
        if 'id' in qs:
            return qs['id'][0]
        if parts:
            return '/'.join(parts[:3]) if len(parts) >= 3 else '/'.join(parts)

    elif 'tiktok.com' in domain or 'vm.tiktok.com' in domain:
        # Username is first part, possibly with @
        if parts:
            return parts[0].lstrip('@')

    elif 'etsy.com' in domain or domain.endswith('.etsy.com'):
        # Shop name is second part or subdomain
        if domain.endswith('.etsy.com') and domain != 'etsy.com':
            return domain.split('.')[0]
        if len(parts) >= 2 and parts[0] == 'shop':
            return parts[1]
        return '/'.join(parts)

    elif 'poshmark.com' in domain:
        # /closet/{username}
        if len(parts) >= 2 and parts[0] == 'closet':
            return parts[1]

    elif 'ebay.com' in domain or 'ebay.us' in domain:
        # /str/{storename} or /usr/{username}
        if len(parts) >= 2 and parts[0] in ['str', 'usr']:
            return parts[1]

    elif 'mercari.com' in domain or 'merc.li' in domain:
        # /u/{id}
        if len(parts) >= 2 and parts[0] == 'u':
            return parts[1]
        return '/'.join(parts)

    elif 'collx.app' in domain or 'share.collx.app' in domain:
        # Username is last part
        if parts:
            return parts[-1]

    # Default: join all path parts
    return '/'.join(parts)


def compare_identifiers(orig_id: str, visited_id: str) -> Tuple[bool, List[int], str]:
    """
    Character-by-character comparison of identifiers.

    Returns: (match, diff_positions, diff_summary)
    """
    if orig_id == visited_id:
        return True, [], 'Exact match'

    # Normalize for comparison (case-insensitive)
    orig_lower = orig_id.lower()
    visited_lower = visited_id.lower()

    if orig_lower == visited_lower:
        return True, [], 'Case-insensitive match'

    # Find character differences
    diff_positions = []
    max_len = max(len(orig_id), len(visited_id))

    for i in range(max_len):
        orig_char = orig_id[i] if i < len(orig_id) else None
        visited_char = visited_id[i] if i < len(visited_id) else None

        if orig_char != visited_char:
            diff_positions.append(i)

    # Build summary
    if not diff_positions:
        summary = 'Case difference only'
    elif len(diff_positions) == 1:
        pos = diff_positions[0]
        orig_char = orig_id[pos] if pos < len(orig_id) else '<end>'
        visited_char = visited_id[pos] if pos < len(visited_id) else '<end>'
        summary = f'1 char diff at position {pos}: "{orig_char}" vs "{visited_char}"'
    elif len(diff_positions) <= 5:
        summary = f'{len(diff_positions)} character differences at positions: {diff_positions}'
    else:
        summary = f'{len(diff_positions)} character differences detected'

    # Length difference
    if len(orig_id) != len(visited_id):
        summary += f' (length: {len(orig_id)} → {len(visited_id)})'

    return False, diff_positions, summary


def verify_url_pair(original: str, visited: str) -> Dict[str, Any]:
    """
    Verify integrity between original and visited URLs.

    Returns verification result with detailed comparison.
    """
    orig_id = extract_identifier(original)
    visited_id = extract_identifier(visited)

    match, diff_positions, diff_summary = compare_identifiers(orig_id, visited_id)

    recommendation = 'ok' if match else 'trust_original'

    return {
        'match': match,
        'original_path': orig_id,
        'visited_path': visited_id,
        'diff_positions': diff_positions,
        'diff_summary': diff_summary,
        'recommendation': recommendation,
        'original_url': original,
        'visited_url': visited
    }


def main():
    parser = argparse.ArgumentParser(description='Verify URL integrity by comparing identifiers')
    parser.add_argument('--original', help='Original URL')
    parser.add_argument('--visited', help='Visited/resolved URL')
    parser.add_argument('--batch', action='store_true', help='Batch mode: read JSON array from stdin')
    parser.add_argument('--input', help='Input JSON file')

    args = parser.parse_args()

    if args.batch or (not args.original and not args.visited):
        # Batch mode
        if args.input:
            with open(args.input, 'r') as f:
                data = json.load(f)
        else:
            data = json.load(sys.stdin)

        if not isinstance(data, list):
            data = [data]

        results = []
        for item in data:
            if isinstance(item, dict):
                result = verify_url_pair(item.get('original', ''), item.get('visited', ''))
                results.append(result)

        print(json.dumps(results, indent=2))
    else:
        # Single pair mode
        if not args.original or not args.visited:
            print(json.dumps({
                'error': 'Must provide --original and --visited, or use --batch mode'
            }), file=sys.stderr)
            sys.exit(1)

        result = verify_url_pair(args.original, args.visited)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
