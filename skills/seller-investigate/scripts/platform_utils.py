#!/usr/bin/env python3
"""
Shared platform detection & identifier extraction.

Single source of truth for:
  - domain → platform name classification
  - extracting the meaningful identifier (username, shop name, numeric id)
    from a platform URL.

Used by both normalize_urls.py and verify_url_integrity.py so the same
platform-aware rules stay in sync.
"""

from typing import Optional
from urllib.parse import urlparse, parse_qs


# Order matters: first matcher wins. Domains are already lowercased and
# stripped of a leading "www." before matching.
PLATFORM_MATCHERS = [
    ('instagram', lambda d: 'instagram.com' in d),
    ('whatnot',   lambda d: 'whatnot.com' in d),
    ('facebook',  lambda d: 'facebook.com' in d or d == 'fb.me'),
    # 'tiktok.com' in d already catches 'vm.tiktok.com'
    ('tiktok',    lambda d: 'tiktok.com' in d),
    ('etsy',      lambda d: 'etsy.com' in d or d.endswith('.etsy.com')),
    ('poshmark',  lambda d: 'poshmark.com' in d),
    ('ebay',      lambda d: 'ebay.com' in d or 'ebay.us' in d),
    ('mercari',   lambda d: 'mercari.com' in d or 'merc.li' in d),
    # 'collx.app' in d already catches 'share.collx.app'
    ('collx',     lambda d: 'collx.app' in d),
]


def canonical_domain(netloc: str) -> str:
    """Lowercase + strip www. prefix."""
    return (netloc or '').lower().replace('www.', '', 1) if netloc else ''


def detect_platform(domain: str) -> str:
    """
    Classify a domain to a platform name.

    Returns one of: 'instagram', 'whatnot', 'facebook', 'tiktok', 'etsy',
    'poshmark', 'ebay', 'mercari', 'collx', or 'unknown'.
    """
    d = canonical_domain(domain)
    for name, matcher in PLATFORM_MATCHERS:
        if matcher(d):
            return name
    return 'unknown'


def extract_identifier(url: str) -> str:
    """
    Extract the meaningful identifier (username, shop name, numeric id)
    from a platform URL. Used by verify_url_integrity.py for character-level
    diffing of original vs. visited URLs.

    Examples:
      instagram.com/fayefree_succulents → 'fayefree_succulents'
      ebay.com/str/STORENAME            → 'STORENAME'
      etsy.com/shop/shopname            → 'shopname'
      granitestatecoins.etsy.com        → 'granitestatecoins'
      facebook.com/profile.php?id=123   → '123'
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return ''

    domain = canonical_domain(parsed.netloc)
    path = parsed.path.strip('/')
    platform = detect_platform(domain)

    # Etsy subdomain stores the identifier in the domain itself
    # (e.g. granitestatecoins.etsy.com), so it's valid even when the path
    # is empty. Handle this BEFORE the empty-path early return so callers
    # like normalize_urls.py (which compute expected_identifier off the
    # normalized URL) get the right answer.
    if (
        platform == 'etsy'
        and domain.endswith('.etsy.com')
        and domain != 'etsy.com'
        and not path
    ):
        return domain.split('.')[0]

    if not path:
        return ''

    parts = [p for p in path.split('/') if p]

    if platform == 'instagram':
        return parts[0] if parts else ''

    if platform == 'whatnot':
        if len(parts) >= 2 and parts[0] in ('user', 's', 'invite'):
            return parts[1]
        if len(parts) == 1:
            return parts[0]
        return ''

    if platform == 'facebook':
        if parts and parts[0] != 'profile.php':
            return parts[0]
        qs = parse_qs(parsed.query)
        if 'id' in qs:
            return qs['id'][0]
        if parts:
            return '/'.join(parts[:3]) if len(parts) >= 3 else '/'.join(parts)
        return ''

    if platform == 'tiktok':
        return parts[0].lstrip('@') if parts else ''

    if platform == 'etsy':
        if domain.endswith('.etsy.com') and domain != 'etsy.com':
            return domain.split('.')[0]
        if len(parts) >= 2 and parts[0] == 'shop':
            return parts[1]
        return '/'.join(parts)

    if platform == 'poshmark':
        if len(parts) >= 2 and parts[0] == 'closet':
            return parts[1]
        return ''

    if platform == 'ebay':
        if len(parts) >= 2 and parts[0] in ('str', 'usr'):
            return parts[1]
        return ''

    if platform == 'mercari':
        if len(parts) >= 2 and parts[0] == 'u':
            return parts[1]
        return '/'.join(parts)

    if platform == 'collx':
        return parts[-1] if parts else ''

    # Unknown platform — join path parts as best-effort identifier.
    return '/'.join(parts)
