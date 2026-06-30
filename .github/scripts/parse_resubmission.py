"""
Parse a GLIMS Ingest Resubmission/Correction GitHub issue form submission
and write the result to data/resubmission_<issue_number>.json.

Expected environment variables (set by the workflow):
    ISSUE_BODY      - JSON-encoded issue body string
    ISSUE_NUMBER    - issue number
    ISSUE_URL       - full URL to the issue
    CREATED_AT      - ISO 8601 creation timestamp
"""

import json
import os
import re
import sys
from pathlib import Path


def parse_section(body: str, heading: str) -> str | None:
    """Extract the value under a ### heading from a GitHub issue form body."""
    escaped = re.escape(heading)
    pattern = rf'###\s*{escaped}\s*\n+([\s\S]*?)(?=\n###|$)'
    match = re.search(pattern, body)
    if not match:
        return None
    value = match.group(1).strip()
    return None if value in ('_No response_', '') else value


def parse_checkboxes(body: str, heading: str) -> list[str]:
    """
    Extract checked items from a GitHub issue form checkboxes field.
    Checked items render as '- [X] Label'; unchecked as '- [ ] Label'.
    """
    raw = parse_section(body, heading)
    if not raw:
        return []
    checked = []
    for line in raw.splitlines():
        match = re.match(r'-\s*\[(x|X)\]\s*(.+)', line.strip())
        if match:
            checked.append(match.group(2).strip())
    return checked


def validate_fields(entry: dict) -> list[str]:
    """Return a list of validation error messages."""
    errors = []

    if not entry.get('original_submission'):
        errors.append('Original submission ID is required but was not found.')

    if not entry.get('reason'):
        errors.append('Reason for resubmission is required but was not found.')

    if not entry.get('notes'):
        errors.append('Additional notes are required but were not found.')

    link = entry.get('previous_issue_link')
    if link and not link.startswith('https://github.com/'):
        errors.append(
            f'previous_issue_link "{link}" does not look like a GitHub URL.'
        )

    return errors


def main():
    body_json = os.environ['ISSUE_BODY']
    issue_number = int(os.environ['ISSUE_NUMBER'])
    issue_url = os.environ['ISSUE_URL']
    created_at = os.environ['CREATED_AT']

    body = json.loads(body_json)

    entry = {
        'issue_number': issue_number,
        'issue_url': issue_url,
        'created_at': created_at,
        'original_submission': parse_section(body, 'Original submission ID'),
        'previous_issue_link': parse_section(
            body, 'Link to previous submission issue/PR'
        ),
        'reason': parse_section(body, 'Reason for resubmission'),
        'scope': parse_checkboxes(body, 'Scope of change'),
        'notes': parse_section(body, 'Additional notes'),
    }

    errors = validate_fields(entry)
    if errors:
        print('Validation errors:', flush=True)
        for e in errors:
            print(f'  - {e}', flush=True)
        sys.exit(1)

    print(f'Parsed entry:\n{json.dumps(entry, indent=2)}', flush=True)

    out_path = Path('data') / f'resubmission_{issue_number}.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(entry, indent=2))
    print(f'Written to {out_path}', flush=True)


if __name__ == '__main__':
    main()
