"""Parsers for GitHub issues"""

import re


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
