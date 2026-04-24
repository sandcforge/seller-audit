#!/usr/bin/env python3
"""
URL Normalization & Validation

Translates URL normalization rules from url-normalization.md into deterministic Python code.
Handles platform detection, specific normalization, junk detection, and Chrome visit marking.
"""

import json
import sys
import re
import argparse
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from platform_utils import detect_platform


def normalize_url(url: str) -> Tuple[str, str, bool, str, str]:
    """
    Normalize a single URL and detect platform.

    Returns: (normalized_url, platform, is_junk, junk_reason, notes)
    """
    original = url.strip().strip('"\'')

    # Detect if it looks like an email or obvious junk (@ without :// AND not a TikTok handle)
    if '@' in original and '://' not in original and not original.startswith('@'):
        # Check if it's actually tiktok.com/@username format
        if 'tiktok.com/@' not in original:
            return original, 'unknown', True, 'email_address', 'Email in URL field'

    # Fix broken protocols
    if original.lower().startswith('http//'):
        original = 'https://' + original[7:]
    elif original.lower().startswith('htp://'):
        original = 'https://' + original[6:]
    elif original.lower().startswith('http:'):
        original = 'https:' + original[5:]
    elif not original.lower().startswith(('http://', 'https://', 'www.')):
        # Check if it looks like a URL
        if any(x in original for x in ['.com', '.app', '.io']):
            # Special case: tiktok.com/@username needs protocol
            original = 'https://' + original
        else:
            # Try to extract URL from free text or treat as username
            extracted = extract_url_from_text(original)
            if extracted:
                original = extracted
            else:
                return original, 'unknown', True, 'not_a_url', 'Not a valid URL format'

    if original.lower().startswith('www.'):
        original = 'https://' + original

    # Strip www and normalize scheme
    try:
        parsed = urlparse(original)
    except Exception:
        return original, 'unknown', True, 'invalid_url', 'Failed to parse URL'

    # Detect platform
    domain = parsed.netloc.lower().replace('www.', '')
    path = parsed.path

    platform, normalized, notes = normalize_by_platform(domain, path, parsed)

    # Check for junk conditions
    is_junk = False
    junk_reason = ''

    if normalized is None:
        is_junk = True
        junk_reason = notes
        normalized = original
    elif domain in ['instagram.com', 'tiktok.com', 'facebook.com', 'whatnot.com',
                     'etsy.com', 'poshmark.com', 'ebay.com', 'mercari.com']:
        # Check for homepage-only junk
        if not path or path == '/':
            is_junk = True
            junk_reason = 'platform_homepage_only'
            notes = f'No username/path for {platform}'

    return normalized, platform, is_junk, junk_reason, notes if not is_junk else ''


def extract_url_from_text(text: str) -> str:
    """Extract URL from free text like 'my store is whatnot.com/user/abc'"""
    # Simple regex for URLs
    match = re.search(r'(https?://)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)', text)
    if match:
        url = match.group(2)
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    return ''


def normalize_by_platform(domain: str, path: str, parsed) -> Tuple[str, str, str]:
    """
    Apply platform-specific normalization rules.
    Platform classification comes from platform_utils.detect_platform so the
    set of supported domains stays in lockstep with verify_url_integrity.
    Returns: (platform_name, normalized_url, notes)
    """
    scheme = 'https'
    platform = detect_platform(domain)
    parts = [p for p in path.split('/') if p]

    if platform == 'instagram':
        if not path or path == '/':
            return 'instagram', None, 'instagram_homepage_only'

        if len(parts) > 0:
            first = parts[0]
            # Single reel/post — needs Chrome visit to extract the author.
            if first in ['reel', 'p']:
                normalized = f'{scheme}://{domain}{path}'
                notes = f'Single {first}, extract username from page'
                return 'instagram', normalized, notes
            query = strip_tracking_params(parsed.query)
            url = f'{scheme}://{domain}/{first}'
            if query:
                url += f'?{query}'
            return 'instagram', url, 'valid_profile'

        return 'instagram', None, 'invalid_instagram_path'

    if platform == 'whatnot':
        if not path or path == '/':
            return 'whatnot', None, 'whatnot_homepage_only'

        if len(parts) >= 2:
            if parts[0] == 's':
                normalized = f'{scheme}://{domain}{path}'
                return 'whatnot', normalized, 'short_link_auto_redirect'
            if parts[0] == 'user':
                query = strip_tracking_params(parsed.query)
                url = f'{scheme}://{domain}/user/{parts[1]}'
                if query:
                    url += f'?{query}'
                return 'whatnot', url, 'valid_profile'
            if parts[0] == 'invite':
                query = strip_tracking_params(parsed.query)
                url = f'{scheme}://{domain}/user/{parts[1]}'
                if query:
                    url += f'?{query}'
                return 'whatnot', url, 'invite_converted_to_user'
            if parts[0] == 'live':
                normalized = f'{scheme}://{domain}{path}'
                return 'whatnot', normalized, 'live_stream_extract_seller'

        return 'whatnot', None, 'invalid_whatnot_path'

    if platform == 'facebook':
        if domain == 'fb.me':
            if not path or path == '/':
                return 'facebook', None, 'fb_homepage_only'
            return 'facebook', f'{scheme}://{domain}{path}', 'short_link_auto_redirect'

        if not path or path == '/':
            return 'facebook', None, 'facebook_homepage_only'

        if len(parts) > 0:
            if parts[0] == 'groups':
                return 'facebook', None, 'facebook_group_link'
            if parts[0] == 'marketplace':
                return 'facebook', f'{scheme}://{domain}{path}', 'marketplace_profile'
            if parts[0] == 'profile.php':
                return 'facebook', f'{scheme}://{domain}{path}', 'numeric_profile'
            if parts[0] == 'share':
                return 'facebook', f'{scheme}://{domain}{path}', 'share_link_visit'
            query = strip_tracking_params(parsed.query)
            url = f'{scheme}://{domain}/{parts[0]}'
            if query:
                url += f'?{query}'
            return 'facebook', url, 'valid_profile'

        return 'facebook', None, 'invalid_facebook_path'

    if platform == 'tiktok':
        if 'vm.tiktok.com' in domain:
            if not path or path == '/':
                return 'tiktok', None, 'vm_tiktok_homepage_only'
            return 'tiktok', f'{scheme}://{domain}{path}', 'short_link_auto_redirect'

        if not path or path == '/':
            return 'tiktok', None, 'tiktok_homepage_only'

        if len(parts) > 0:
            username = parts[0]
            if not username.startswith('@'):
                username = '@' + username

            query = strip_tracking_params(parsed.query, ['_t', 'is_from_webapp'])
            url = f'{scheme}://{domain}/{username}'
            if query:
                url += f'?{query}'

            notes = 'added_@ ' if not parts[0].startswith('@') else 'valid_profile'
            return 'tiktok', url, notes

        return 'tiktok', None, 'invalid_tiktok_path'

    if platform == 'etsy':
        if domain.endswith('.etsy.com') and domain != 'etsy.com':
            return 'etsy', f'{scheme}://{domain}', 'subdomain_format'

        if not path or path == '/':
            return 'etsy', None, 'etsy_homepage_only'

        if len(parts) >= 2:
            if parts[0] == 'shop':
                query = strip_tracking_params(parsed.query)
                url = f'{scheme}://{domain}/shop/{parts[1]}'
                if query:
                    url += f'?{query}'
                return 'etsy', url, 'valid_shop'
            if parts[0] == 'listing':
                return 'etsy', f'{scheme}://{domain}{path}', 'single_listing_extract_shop'
            if parts[0] == 'people':
                return 'etsy', None, 'etsy_buyer_profile_not_shop'

        return 'etsy', None, 'invalid_etsy_path'

    if platform == 'poshmark':
        if not path or path == '/':
            return 'poshmark', None, 'poshmark_homepage_only'

        if len(parts) >= 2:
            if parts[0] == 'closet':
                query = strip_tracking_params(parsed.query)
                url = f'{scheme}://{domain}/closet/{parts[1]}'
                if query:
                    url += f'?{query}'
                return 'poshmark', url, 'valid_closet'
            if parts[0] == 'listing':
                return 'poshmark', f'{scheme}://{domain}{path}', 'single_listing_extract_seller'

        return 'poshmark', None, 'invalid_poshmark_path'

    if platform == 'ebay':
        if 'ebay.us' in domain and '/m/' in path:
            return 'ebay', f'{scheme}://{domain}{path}', 'short_link_auto_redirect'

        if not path or path == '/':
            return 'ebay', None, 'ebay_homepage_only'

        if len(parts) >= 2:
            if parts[0] == 'usr':
                return 'ebay', f'{scheme}://{domain}/usr/{parts[1]}', 'valid_profile'
            if parts[0] == 'str':
                return 'ebay', f'{scheme}://{domain}/str/{parts[1]}', 'valid_store'
            if parts[0] == 'itm':
                return 'ebay', f'{scheme}://{domain}{path}', 'single_listing_extract_seller'

        return 'ebay', None, 'invalid_ebay_path'

    if platform == 'mercari':
        if 'merc.li' in domain:
            return 'mercari', f'{scheme}://{domain}{path}', 'short_link_auto_redirect'

        if not path or path == '/':
            return 'mercari', None, 'mercari_homepage_only'

        if len(parts) >= 2:
            if parts[0] == 'u':
                return 'mercari', f'{scheme}://{domain}/u/{parts[1]}', 'valid_profile'
            if parts[0] == 'item':
                return 'mercari', f'{scheme}://{domain}{path}', 'single_item_extract_seller'

        return 'mercari', None, 'invalid_mercari_path'

    if platform == 'collx':
        if not path or path == '/':
            return 'collx', None, 'collx_homepage_only'

        if len(parts) > 0:
            return 'collx', f'{scheme}://{domain}{path}', 'valid_profile_use_get_page_text'

        return 'collx', None, 'invalid_collx_path'

    # Unknown platform
    return 'unknown', f'{scheme}://{domain}{path}', 'unknown_platform'


def strip_tracking_params(query: str, extra_params: List[str] = None) -> str:
    """Remove tracking parameters from query string."""
    if not query:
        return ''

    tracking_params = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
        'fbclid', 'gclid', 'ref', 'igsh', 'mibextid', '_t', 'is_from_webapp',
        'referral_source', 'refer'
    }

    if extra_params:
        tracking_params.update(extra_params)

    params = parse_qs(query, keep_blank_values=True)
    clean_params = {k: v for k, v in params.items() if k not in tracking_params}

    if not clean_params:
        return ''

    # Flatten lists back to strings
    result = []
    for k, v in clean_params.items():
        for val in v:
            result.append(f'{k}={val}')

    return '&'.join(result)


def needs_chrome_visit(url: str, notes: str) -> bool:
    """Check if URL needs Chrome visit (short links or single items)."""
    short_link_patterns = [
        'short_link_auto_redirect',
        'single_listing_extract_shop',
        'single_listing_extract_seller',
        'single_item_extract_seller',
        'single_reel',
        'single_post',
        'live_stream_extract_seller',
        'marketplace_profile',
        'numeric_profile',
        'share_link_visit'
    ]

    return any(pattern in notes for pattern in short_link_patterns)


def process_urls(raw_urls: List[str]) -> List[Dict[str, Any]]:
    """Process multiple URLs and return normalized results."""
    results = []
    seen = set()

    for raw_url in raw_urls:
        if not raw_url or not raw_url.strip():
            continue

        # Handle multi-URL fields (comma or space separated)
        urls_to_process = []
        for part in re.split(r'[,\s]+', raw_url):
            part = part.strip()
            if part:
                urls_to_process.append(part)

        for url in urls_to_process:
            normalized, platform, is_junk, junk_reason, notes = normalize_url(url)

            # Deduplicate by normalized URL
            if not is_junk:
                if normalized in seen:
                    continue
                seen.add(normalized)

            result = {
                'original': url.strip().strip('"\''),
                'normalized': normalized if is_junk else None,
                'platform': platform,
                'is_junk': is_junk,
                'junk_reason': junk_reason,
                'notes': notes,
                'needs_chrome_visit': False,
                'needs_seller_extraction': False
            }

            if not is_junk:
                result['normalized'] = normalized
                result['needs_chrome_visit'] = needs_chrome_visit(normalized, notes)
                result['needs_seller_extraction'] = any(
                    x in notes for x in ['extract_username', 'extract_shop', 'extract_seller']
                )

            results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(description='Normalize and validate URLs')
    parser.add_argument('--urls', help='Comma-separated URLs')
    parser.add_argument('--input', help='Input JSON file with URL array')

    args = parser.parse_args()

    urls = []

    if args.urls:
        urls = [u.strip() for u in args.urls.split(',')]
    elif args.input:
        with open(args.input, 'r') as f:
            data = json.load(f)
            urls = data if isinstance(data, list) else [data]
    else:
        # Read from stdin
        data = json.load(sys.stdin)
        urls = data if isinstance(data, list) else [data]

    results = process_urls(urls)
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
