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

from platform_utils import extract_identifier


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
