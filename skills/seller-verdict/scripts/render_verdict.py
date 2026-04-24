#!/usr/bin/env python3
"""
Verdict Renderer

Takes handoff YAML data + agent-provided tier/risk assessment, applies decision matrix,
and renders a Markdown report.

Supports all four category SOPs: General, Plants, Shiny, Beauty, Collectibles.
"""

import json
import sys
import argparse
import yaml
from typing import Dict, Any, List, Tuple
from datetime import datetime


# Decision Matrices (hardcoded from SOPs)

DECISION_MATRIX_GENERAL = {
    'S': {'HIGH': 'REVIEW', 'MEDIUM': 'REVIEW', 'LOW': 'APPROVE'},
    'A': {'HIGH': 'REJECT', 'MEDIUM': 'REVIEW', 'LOW': 'APPROVE'},
    'B': {'HIGH': 'REJECT', 'MEDIUM': 'REVIEW', 'LOW': 'APPROVE'},
    'F': {'HIGH': 'REJECT', 'MEDIUM': 'REJECT', 'LOW': 'REJECT'},
}

DECISION_MATRIX_SHINY = {
    'S': {'HIGH': 'REVIEW', 'MEDIUM': 'REVIEW', 'LOW': 'APPROVE'},
    'A': {'HIGH': 'REJECT', 'MEDIUM': 'REVIEW', 'LOW': 'APPROVE'},
    'B': {'HIGH': 'REJECT', 'MEDIUM': 'REVIEW', 'LOW': 'APPROVE'},
    'F': {'HIGH': 'REJECT', 'MEDIUM': 'REVIEW', 'LOW': 'REJECT'},
}


def get_decision_matrix(category: str) -> Dict[str, Dict[str, str]]:
    """Get the decision matrix for a category."""
    if category == 'plants':
        return {}  # Plants uses custom logic
    elif category == 'shiny':
        return DECISION_MATRIX_SHINY
    elif category == 'beauty':
        return {}  # Beauty uses custom logic
    elif category == 'collectibles':
        return {}  # Collectibles uses custom logic
    else:
        return DECISION_MATRIX_GENERAL


def apply_plants_sop(tier: str, risk: str, has_missing_info: bool) -> Tuple[str, str]:
    """
    Apply Plants SOP decision logic.
    Returns: (verdict, action)
    """
    if has_missing_info:
        return 'REVIEW', 'Contact seller for valid link'

    if risk == 'HIGH':
        if tier == 'S':
            return 'REVIEW', 'Review: High-risk elite seller'
        else:
            return 'REJECT', 'High-risk signal detected'

    if tier == 'S':
        return 'ESCALATE_TO_MADDY', 'Escalate to Maddy for VIP onboarding'
    elif tier == 'A':
        return 'APPROVE', 'CONTACT_SELLER'
    elif tier == 'B':
        return 'APPROVE', 'ROOKIE_SELLER'
    elif tier == 'F':
        return 'REJECT', 'Insufficient tier'

    return 'REVIEW', 'Unable to classify'


def apply_shiny_sop(tier: str, risk: str) -> Tuple[str, str]:
    """
    Apply Shiny SOP decision logic using matrix.
    Returns: (verdict, action)
    """
    matrix = DECISION_MATRIX_SHINY
    verdict = matrix.get(tier, {}).get(risk, 'REVIEW')
    action = f'{tier}/{risk}'
    return verdict, action


def apply_beauty_sop(tier: str, risk: str, vip_referral: bool, pure_influencer: bool) -> Tuple[str, str]:
    """
    Apply Beauty SOP decision logic.
    Returns: (verdict, action)
    """
    if vip_referral or tier == 'S':
        return 'ESCALATE_TO_RAJ', 'Escalate to Raj (VIP/S-Tier)'

    if pure_influencer:
        return 'FLAG_TO_JAMES', 'Flag to James (Influencer/Affiliate candidate)'

    if risk == 'HIGH' or tier == 'F':
        return 'REJECT', f'High-risk or tier F: {tier}/{risk}'

    if (tier == 'A' or tier == 'B') and risk == 'LOW':
        return 'APPROVE', f'Tier {tier}, Low risk'

    return 'REVIEW', f'{tier}/{risk}'


def apply_collectibles_sop(tier: str, risk: str, non_us: bool = False) -> Tuple[str, str]:
    """
    Apply Collectibles SOP decision logic.
    CRITICAL: NEVER reject outright. REJECTs downgrade to REVIEW.
    Returns: (verdict, action)
    """
    if risk in ['HIGH', 'MEDIUM'] or tier == 'F':
        if non_us:
            return 'REVIEW', 'Forward to Kay (International)'
        return 'REVIEW', f'Review: {tier}/{risk}'

    if tier == 'S':
        return 'APPROVE', 'ESCALATE_TO_ME_S_TIER'
    elif tier == 'A':
        return 'APPROVE', 'ESCALATE_TO_ME_A_TIER'
    elif tier == 'B':
        return 'APPROVE', 'Tier B approval'

    return 'REVIEW', f'{tier}/{risk}'


def apply_general_sop(tier: str, risk: str) -> Tuple[str, str]:
    """
    Apply General SOP decision logic using matrix.
    Returns: (verdict, action)
    """
    matrix = DECISION_MATRIX_GENERAL
    verdict = matrix.get(tier, {}).get(risk, 'REVIEW')
    action = f'{tier}/{risk}'
    return verdict, action


def determine_verdict(assessment: Dict[str, Any]) -> Tuple[str, str]:
    """
    Determine verdict based on category and assessment.
    Returns: (verdict, action)
    """
    tier = assessment.get('tier', 'F')
    risk = assessment.get('risk', 'HIGH')
    category = assessment.get('category_used', 'general')
    special_notes = assessment.get('special_notes') or ''

    if category == 'plants':
        has_missing_info = 'missing_info' in special_notes.lower()
        return apply_plants_sop(tier, risk, has_missing_info)

    elif category == 'shiny':
        return apply_shiny_sop(tier, risk)

    elif category == 'beauty':
        vip_referral = 'vip' in special_notes.lower()
        pure_influencer = 'influencer' in special_notes.lower()
        return apply_beauty_sop(tier, risk, vip_referral, pure_influencer)

    elif category == 'collectibles':
        non_us = 'international' in special_notes.lower()
        return apply_collectibles_sop(tier, risk, non_us)

    else:
        return apply_general_sop(tier, risk)


def render_investigation_steps(steps: List[Dict[str, Any]]) -> str:
    """Render investigation steps as markdown."""
    if not steps:
        return ''

    output = '### Investigation Steps\n\n'

    for i, step in enumerate(steps, 1):
        heading = step.get('heading', f'Step {i}')
        url = step.get('url', '')
        status = step.get('status', 'unknown')
        findings = step.get('findings', '')
        signals = step.get('signals', [])

        output += f'**Step {i} — {heading}**\n'

        if url:
            output += f'URL: `{url}`\n'

        output += f'Status: `{status}`\n'

        if findings:
            output += f'\n{findings}\n'

        if signals:
            output += '\nSignals:\n'
            for signal in signals:
                output += f'- {signal}\n'

        output += '\n'

    return output


def render_verdict_section(assessment: Dict[str, Any], handoff: Dict[str, Any]) -> str:
    """Render the verdict section with decision matrix and justification."""
    verdict, action = determine_verdict(assessment)

    tier = assessment.get('tier', 'F')
    risk = assessment.get('risk', 'HIGH')
    category = assessment.get('category_used', 'general')

    # Verdict step is numbered immediately after the last investigation step.
    verdict_step_num = len(assessment.get('investigation_steps', [])) + 1
    output = f'**Step {verdict_step_num} — Verdict: Apply {category.title()} SOP**\n\n'

    output += f'- **Tier:** {tier}\n'
    output += f'- **Risk:** {risk}\n'
    output += f'- **Category:** {category.title()}\n'
    output += f'- **Verdict:** {verdict}\n'
    output += f'- **Action:** {action}\n\n'

    # Add justification
    tier_just = assessment.get('tier_justification', '')
    risk_just = assessment.get('risk_justification', '')

    if tier_just or risk_just:
        output += '**Justification:**\n'
        if tier_just:
            output += f'- Tier: {tier_just}\n'
        if risk_just:
            output += f'- Risk: {risk_just}\n'
        output += '\n'

    return output


def render_report(input_data: Dict[str, Any]) -> str:
    """Render complete markdown report."""
    handoff = input_data.get('handoff', {})
    assessment = input_data.get('assessment', {})

    seller = handoff.get('seller', {})
    contact_id = seller.get('hubspot_id', 'unknown')
    full_name = seller.get('name', 'Unknown Seller')
    company = seller.get('company')

    # Title
    title = full_name
    if company and company != full_name:
        title += f' ({company})'

    output = f'## Seller #{contact_id}: {title}\n\n'

    # HubSpot link
    output += f'**HubSpot:** https://app.hubspot.com/contacts/45316392/record/0-1/{contact_id}\n\n'

    # Summary table
    tier = assessment.get('tier', 'F')
    risk = assessment.get('risk', 'HIGH')
    category = assessment.get('category_used', 'general')
    verdict, action = determine_verdict(assessment)

    output += '| Verdict | Tier | Risk | Category | Action |\n'
    output += '|---------|------|------|----------|--------|\n'
    output += f'| **{verdict}** | {tier} | {risk} | {category.title()} | {action} |\n\n'

    # Summary paragraph
    investigation_steps = assessment.get('investigation_steps', [])
    # Platform counts come from the handoff YAML's investigation_summary, NOT from
    # len(investigation_steps). investigation_steps may include analysis/credibility
    # steps that aren't platform visits, which would inflate the count.
    inv_summary = handoff.get('investigation_summary', {}) if isinstance(handoff, dict) else {}
    platforms_checked = inv_summary.get('total_platforms_checked')
    active_platforms = inv_summary.get('total_platforms_active')
    if platforms_checked is None or active_platforms is None:
        # Fall back to platforms[] length if summary is missing.
        platforms_list = handoff.get('platforms', []) if isinstance(handoff, dict) else []
        platforms_checked = platforms_checked if platforms_checked is not None else len(platforms_list)
        active_platforms = active_platforms if active_platforms is not None else sum(
            1 for p in platforms_list if p.get('status') == 'active'
        )

    summary = f'Audited {platforms_checked} platform{"s" if platforms_checked != 1 else ""} with {active_platforms} active. '
    summary += f'Verdict: **{verdict}**. '
    summary += f'{assessment.get("tier_justification", "Investigation complete.")}\n\n'

    output += f'> {summary}\n\n---\n\n'

    # Investigation steps
    output += render_investigation_steps(investigation_steps)

    # Verdict section
    output += render_verdict_section(assessment, handoff)

    # Special notes
    special_notes = assessment.get('special_notes')
    if special_notes:
        output += f'**Special Notes:**\n{special_notes}\n\n'

    # HubSpot conflict
    conflict = assessment.get('hubspot_status_conflict')
    if conflict:
        output += '**⚠️ HubSpot Status Conflict:**\n'
        output += f'- Existing Status: {conflict.get("existing_status")}\n'
        output += f'- Existing Date: {conflict.get("existing_date")}\n'
        output += f'- Conflict Reason: {conflict.get("conflict_reason")}\n\n'

    return output


def main():
    parser = argparse.ArgumentParser(description='Render verdict report from handoff + assessment')
    parser.add_argument('input_file', nargs='?', help='Input JSON or YAML file')
    parser.add_argument('--format', choices=['json', 'yaml'], default='json', help='Input format')

    args = parser.parse_args()

    # Read input
    if args.input_file:
        with open(args.input_file, 'r') as f:
            if args.format == 'yaml' or args.input_file.endswith('.yaml') or args.input_file.endswith('.yml'):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
    else:
        # Read from stdin
        content = sys.stdin.read()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = yaml.safe_load(content)

    report = render_report(data)
    print(report)

    # Check length
    line_count = len(report.split('\n'))
    if line_count > 90:
        print(f'\n⚠️ Warning: Report exceeds 90 lines ({line_count} lines)', file=sys.stderr)


if __name__ == '__main__':
    # Try to import yaml, fallback to basic YAML parsing if not available
    try:
        import yaml
    except ImportError:
        # Minimal YAML support
        class SimpleYAML:
            @staticmethod
            def safe_load(f):
                import json
                return json.load(f)

        yaml = SimpleYAML()

    main()
