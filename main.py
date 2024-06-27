# Native Python libraries
import argparse
import logging

# Local libraries
from collector import collector
from reports import create_reports

# Third-party libraries


def main():

    args = get_args()

    # Setup logging
    numeric_level = getattr(logging, args.logging.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.logging}')
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s | %(message)s'
    )

    if not args.no_api:
        collector()

    create_reports()

    print('Reports have been created in the "reports" directory.')


def get_args():

    parser = argparse.ArgumentParser(
        prog='so4t_tag_report.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Uses the Stack Overflow for Teams API to create \
        a CSV report with performance metrics for each tag.',
        epilog='Example for Stack Overflow Business: \n'
        'python3 so4t_tag_report.py --url "https://stackoverflowteams.com/c/TEAM-NAME" '
        '--token "YOUR_TOKEN" \n\n'
        'Example for Stack Overflow Enterprise: \n'
        'python3 so4t_tag_report.py --url "https://SUBDOMAIN.stackenterprise.co" '
        '--key "YOUR_KEY" --token "YOUR_TOKEN"\n\n'
    )

    parser.add_argument('--no-api',
                        action='store_true',
                        help='Optional. If API data has already been collected, skip API calls and '
                        'use existing JSON data. This negates the need to supply a URL or token.')
    parser.add_argument('--days',
                        type=int,
                        help='Optional. Only include metrics for content created within the past X '
                        'days. Default is to include all history')
    parser.add_argument('--start-date',
                        type=str,
                        help='Optional. Only include metrics for content created on or after the '
                        'specified date. Format: YYYY-MM-DD')
    parser.add_argument('--end-date',
                        type=str,
                        help='Optional. Only include metrics for content created on or before the '
                        'specified date. Format: YYYY-MM-DD')
    parser.add_argument('--logging',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        default='INFO',
                        help='Optional. Set the logging level. Default is INFO.')

    return parser.parse_args()


if __name__ == "__main__":

    main()
