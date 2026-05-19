"""
Parse a GLIMS extinct glacier GitHub issue form submission and write the
result to data/extinct_glacier_submission_<issue_number>.json.

Expected environment variables (set by the workflow):
    ISSUE_BODY      - JSON-encoded issue body string
    ISSUE_NUMBER    - issue number
    ISSUE_URL       - full URL to the issue
    CREATED_AT      - ISO 8601 creation timestamp
    GITHUB_TOKEN    - token for fetching private attachments
"""

import io
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# GLIMS glacier ID pattern: G + 6 digits + E/W + 5 digits + N/S
# ---------------------------------------------------------------------------
GLIMS_ID_RE = re.compile(r'^G\d{6}[EW]\d{5}[NS]$', re.IGNORECASE)

# ---------------------------------------------------------------------------
# Date and integer validation patterns
# ---------------------------------------------------------------------------
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def is_valid_glims_id(value: str) -> bool:
    return bool(GLIMS_ID_RE.match(value.strip()))


def parse_section(body: str, heading: str) -> str | None:
    """Extract the value under a ### heading from a GitHub issue form body."""
    escaped = re.escape(heading)
    pattern = rf'###\s*{escaped}\s*\n+([\s\S]*?)(?=\n###|$)'
    match = re.search(pattern, body)
    if not match:
        return None
    value = match.group(1).strip()
    return None if value in ('_No response_', '') else value


def fetch_attachment(url: str, token: str) -> bytes:
    """Download a GitHub attachment, following redirects."""
    headers = {
        'Authorization': f'token {token}',
        'User-Agent': 'github-actions',
    }
    response = requests.get(url, headers=headers, allow_redirects=True)
    response.raise_for_status()
    return response.content


def ids_from_text(text: str) -> list[str]:
    """Parse GLIMS IDs from plain pasted text, one per line."""
    return [
        line.strip()
        for line in text.splitlines()
        if is_valid_glims_id(line.strip())
    ]


def ids_from_attachment(raw: str, token: str) -> tuple[list[str], str | None]:
    """
    If raw contains a GitHub attachment link, fetch and parse it.
    Returns (ids, source_label) where source_label is 'file' or None.
    """
    link_match = re.search(
        r'\[.*?\]\((https://github\.com/[^)]+)\)', raw
    )
    if not link_match:
        return [], None

    url = link_match.group(1)
    ext = url.split('?')[0].rsplit('.', 1)[-1].lower()
    print(f'Detected attachment: {url} (type: {ext})', flush=True)

    content = fetch_attachment(url, token)

    if ext == 'txt':
        ids = [
            line.strip()
            for line in content.decode('utf-8').splitlines()
            if is_valid_glims_id(line.strip())
        ]
        return ids, 'file'

    if ext == 'csv':
        df = pd.read_csv(io.BytesIO(content), header=0, usecols=[0], dtype=str)
        ids = [
            v.strip()
            for v in df.iloc[:, 0].dropna()
            if is_valid_glims_id(v.strip())
        ]
        return ids, 'file'

    if ext == 'xlsx':
        df = pd.read_excel(
            io.BytesIO(content), sheet_name=0, header=0, usecols=[0], dtype=str
        )
        ids = [
            v.strip()
            for v in df.iloc[:, 0].dropna()
            if is_valid_glims_id(v.strip())
        ]
        return ids, 'file'

    print(f'Unsupported attachment type: {ext} — skipping file', flush=True)
    return [], None


def parse_glacier_ids(raw: str, token: str) -> tuple[list[str], str]:
    """
    Merge IDs from pasted text and any file attachment.
    Deduplicates while preserving order (text first, then file).
    Returns (ids, source_label).
    """
    text_ids = ids_from_text(raw)
    file_ids, file_source = ids_from_attachment(raw, token)

    if text_ids and file_ids:
        # Merge, deduplicate, preserve order
        seen = set()
        merged = []
        for id_ in text_ids + file_ids:
            if id_ not in seen:
                seen.add(id_)
                merged.append(id_)
        return merged, 'text+file'

    if file_ids:
        return file_ids, 'file'

    return text_ids, 'text'


def validate_fields(entry: dict) -> list[str]:
    """Return a list of validation error messages."""
    errors = []

    date = entry.get('est_disappear_date')
    if date and not DATE_RE.match(date):
        errors.append(
            f'est_disappear_date "{date}" is not in YYYY-MM-DD format.'
        )

    glims_date = entry.get('glims_added_extinct_date')
    if glims_date and not DATE_RE.match(glims_date):
        errors.append(
            f'glims_added_extinct_date "{glims_date}" is not in YYYY-MM-DD format.'
        )

    unc = entry.get('est_disappear_unc')
    if unc is not None:
        try:
            int(unc)
        except (ValueError, TypeError):
            errors.append(
                f'est_disappear_unc "{unc}" is not a valid integer.'
            )

    if not entry.get('glacier_ids'):
        errors.append('No valid GLIMS glacier IDs were found.')

    return errors


def main():
    # Read environment variables set by the workflow
    body_json = os.environ['ISSUE_BODY']
    issue_number = int(os.environ['ISSUE_NUMBER'])
    issue_url = os.environ['ISSUE_URL']
    created_at = os.environ['CREATED_AT']
    token = os.environ['GITHUB_TOKEN']

    # ISSUE_BODY is JSON-encoded by toJSON() in the workflow
    body = json.loads(body_json)

    glacier_ids_raw = parse_section(body, 'Glacier IDs')
    glacier_ids, ids_source = parse_glacier_ids(glacier_ids_raw or '', token)

    unc_raw = parse_section(
        body, 'Disappearance date uncertainty in days (`est_disappear_unc`)'
    )

    entry = {
        'issue_number': issue_number,
        'issue_url': issue_url,
        'created_at': created_at,
        'glacier_ids': glacier_ids,
        'glacier_ids_source': ids_source,
        'est_disappear_date': parse_section(
            body, 'Estimated disappearance date (`est_disappear_date`)'
        ),
        'est_disappear_unc': int(unc_raw) if unc_raw and unc_raw.strip().isdigit() else unc_raw,
        'gone_source': parse_section(body, 'Source (`gone_source`)'),
        'glims_added_extinct_date': parse_section(
            body, 'Date added to GLIMS as extinct (`glims_added_extinct_date`)'
        ),
        'notes': parse_section(body, 'Additional notes'),
    }

    errors = validate_fields(entry)
    if errors:
        print('Validation errors:', flush=True)
        for e in errors:
            print(f'  - {e}', flush=True)
        sys.exit(1)

    print(f'Parsed entry:\n{json.dumps(entry, indent=2)}', flush=True)

    out_path = Path('data') / f'extinct_glacier_submission_{issue_number}.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(entry, indent=2))
    print(f'Written to {out_path}', flush=True)


if __name__ == '__main__':
    main()
