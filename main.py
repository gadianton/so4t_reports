# Native Python libraries
import argparse

# Local libraries
from collector import collector
from reports import create_reports

# Third-party libraries


def main():

    args = get_args()

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
        epilog = 'Example for Stack Overflow Business: \n'
                'python3 so4t_tag_report.py --url "https://stackoverflowteams.com/c/TEAM-NAME" '
                '--token "YOUR_TOKEN" \n\n'
                'Example for Stack Overflow Enterprise: \n'
                'python3 so4t_tag_report.py --url "https://SUBDOMAIN.stackenterprise.co" '
                '--key "YOUR_KEY" --token "YOUR_TOKEN"\n\n')
    
    parser.add_argument('--no-api',
                        action='store_true',
                        help='If API data has already been collected, skip API calls and use '
                        'existing JSON data. This negates the need for --url, --token, or --key.')
    parser.add_argument('--days',
                        type=int,
                        help='Only include metrics for content created within the past X days. '
                        'Default is to include all history')
    parser.add_argument('--web-client',
                        action='store_true',
                        help='Enables web client for extra data not available via API. Will '
                        'open a Chrome window and prompt manual login.')

    return parser.parse_args()

if __name__ == "__main__":

    main()