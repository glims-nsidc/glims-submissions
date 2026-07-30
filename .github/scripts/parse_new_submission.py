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

from parser import parse_section, parse_checkboxes


def get_data_source_type(body: str) -> dict:
    """Return dict of data source types used in analysis"""
    data_source = parse_checkboxes(
        body,
        'What types of source data were used to map outlines?'
        )
    return data_source


def get_processing(body: str) -> dict:
    """Return processing 

    Arguments:
      body : body returned from New Submisson issue

    Returns:
      dict of processing applied to image

    
    transform_to_projected_coordinates: a transformation from geographic to projected coordinates was performed
    georegistration_with_gcps: image was georegistered using ground control points
    orthorectified: image was corrected for topographic distortion
    radiometric_calibration: convert raw sensor DN to at sensor radiances 
    solar_geometry_correction: surface radiance corrected for solar geometry to get reflectance of a flat surface(?)
    image_radiometric_correction: atmospheric parameters estimated from the image
    model_radiometric_correction: atmospheric model used for correction
    anisotropic_reflectance_correction: non-Lambertian surface reflectance accounted for  
    slope_aspect_correction: surface radiance corrected for topography
    band_ratio_transformation: band ratio applied to image data 
    spatial_filtering_applied: spatial filter applied to image 
    geomorphological_analysis: surface topography evaluated
    texture_analysis: spatial variation in gray levels or brightness calculated
    """

    lookup = {
        'Was image transformed from latitude, longitude to projected coordinates?': 'transform_to_projected_coordinates',
        'Was image converted from image coordinates to geographic coordinates?': 'georegistration_with_gcps',
        'Was image orthorectified?': 'orthorectified',
        'Was image DN converted to radiance?': 'radiometric_calibration',
        'Was image corrected for solar geometry?': 'solar_geometry_correction',
        'Was image radiometrically corrected?': 'image_radiometric_correction',
        'Was a model radiometric correction applied?': 'model_radiometric_correction',
        'Was image corrected for anisotropic reflectance?': 'anisotropic_reflectance_correction',
        'Was a terrain correction applied?': 'slope_aspect_correction',
        'Was a band ratio or linear transform used?': 'band_ratio_transformation',
        'Was spatial filtering used?': 'spatial_filtering_applied',
        'Was geomorphological analysis used?': 'geomorphological_analysis',
        'Was texture analysis used?': 'texture_analysis',
        }

    processing = parse_checkboxes(body, 'Processing')
    result = {
        v: (True if k in processing else False)
        for k, v in lookup.items()
        }

    return result


def parse_analysts(body: str) -> list[str]:
    """Parse analysts section of new submission issue
    and return list of analysts.

    Arguments:
      body : body returned from GitHub call

    Returns:
      list of analysts as string
    """
    analysts = parse_section(body, 'Analysts').split('\n')
    return analysts


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
        'source_data_type': parse_checkboxes(body, 'What type of source data were used to map outlines.  Please select all that apply.'),
        'processing': parse_checkboxes(body, 'Processing'),
        'mapping_process': parse_section(body, 'Please briefly describe your mapping method'),
        'digitization_method': parse_section(body, 'Method of digitization')
        'percent_manual_digitized': parse_section(body, 'What percentage of outlines were manually edited?'),
        'classification_method': parse_section(body, 'Type of classification used'),
        'supervised_method': parse_section(body, 'Type name of supervised classification method if used'),
        'unsupervised_method': parse_section(body, 'Type name of unsupervised classification method if used'),
        'embargo_period_months': parse_section(body, 'Embargo period'),
        'mapping_tool': parse_section(body, 'Name of tool/platform used for mapping'),
        'publication': parse_section(body, 'Publication'),
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

