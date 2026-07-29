"""
Parse a GLIMS Ingest new submission GitHub issue form submission
and write the result to data/new_submission_<issue_number>.json.

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


def parse_issue_body(body: str) -> dict:
    """Parses the body of a new submission issues

    Arguments:
      body : string containing body of issue

    Returns:
      dict containing fields from issue
    """
    issue_dict = {
        'region_center_id': parse_section(body, 'Regional Center ID'),
        'geographic_region': parse_section(body, 'Geographic Region'),
        'submitter': parse_section(body, 'Your Name'),  # need to parse address
        'analysts': parse_analysts(body),  # loop through lines
        'outline_file': parse_section(body, 'Glacier outline file'),
        'outline_file_size': parse_section(body, 'Glacier outline file size in bytes'),
        'source_file': parse_section(body, 'Data sources file names'),
        'additional_files': parse_section(body, 'Additional files'),
        'analysis_date': parse_section(body, 'Date analysis was performed'),
        'source_data_type': parse_section(body, 'What type of source data were used to map outlines.  Please select all that apply.'),
        }

    return issue_dict

    
def main():
    body_json = os.environ['ISSUE_BODY']
    issue_number = int(os.environ['ISSUE_NUMBER'])
    issue_url = os.environ['ISSUE_URL']
    created_at = os.environ['CREATED_AT']

    body = json.loads(body_json)

#    entry = {
#        'issue_number': issue_number,
#        'issue_url': issue_url,
#        'created_at': created_at,
#        'original_submission': parse_section(body, 'Original submission ID'),
#        'previous_issue_link': parse_section(
#            body, 'Link to previous submission issue/PR'
#        ),
#        'reason': parse_section(body, 'Reason for resubmission'),
#        'scope': parse_checkboxes(body, 'Scope of change'),
#        'notes': parse_section(body, 'Additional notes'),
#    }

#    errors = validate_fields(entry)
#    if errors:
#        print('Validation errors:', flush=True)
#        for e in errors:
#            print(f'  - {e}', flush=True)
#        sys.exit(1)

    print(f'Parsed entry:\n{json.dumps(body, indent=2)}', flush=True)

    out_path = Path('data') / f'resubmission_{issue_number}.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(body, indent=2))
    print(f'Written to {out_path}', flush=True)


if __name__ == '__main__':
    main()

