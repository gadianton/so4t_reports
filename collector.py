# Native Python Libraries
from dotenv import load_dotenv
import os

# Open Source Libraries
from so4t_api import StackClient

# Local Libraries
# from api_config import BASE_URL, API_KEY, API_TOKEN, PROXY_URL
from so4t_api_v2 import V2Client

DATA_DIR = 'data'
load_dotenv()  # load environment variables from file (if any)


def collector():

    try:
        url = os.environ['SO_URL']
        token = os.environ['SO_TOKEN']
        if 'stackoverflowteams.com' in url:
            key = None  # Only needed for Enterprise
        else:
            key = os.environ['SO_KEY']
        proxy_url = os.getenv('SO_PROXY_URL')  # proxy is optional (as needed)
    except KeyError:
        print('Environment variables not found. Please enter the API configuration manually.')
        url = input('Enter the URL for your Stack Overflow instance: ')
        token = input('Enter your API token: ')
        if 'stackoverflowteams.com' in url:
            key = None
        else:
            key = input('Enter your API key: ')
        proxy_url = input('Enter the proxy URL (leave blank if not needed): ')

    # Instantiate API and database (DB) clients
    v2client = V2Client(url, token=token, key=key,
                        proxy=proxy_url)
    v3client = StackClient(url, token=token, proxy=proxy_url)

    # Get API data from v2 and v3 clients
    # and store them in them in new, temporary collections in the database
    api_data = {
        "questions": get_questions_answers_comments(v2client),  # also gets answers/comments
        "articles": get_articles(v2client),
        "tags": get_tags(v3client),  # also gets tag SMEs
        "users": get_users(v2client, v3client),
        "user_groups": get_user_groups(v3client),
        "communities": get_communities(v3client),
        "collections": get_collections(v3client),
    }
    api_data['reputation_history'] = get_reputation_history(v2client, api_data['users']),

    # Store the API data in JSON files
    for name, data in api_data.items():
        v3client.export_to_json(name, data, DATA_DIR)


def get_questions_answers_comments(v2client):

    # The API filter used for the /questions endpoint makes it so that the API returns
    # all answers and comments for each question. This is more efficient than making
    # separate API calls for answers and comments.
    # Filter documentation: https://api.stackexchange.com/docs/filters
    if v2client.soe:  # Stack Overflow Enterprise requires the generation of a custom filter
        filter_attributes = [
            "answer.body",
            "answer.body_markdown",
            "answer.comment_count",
            "answer.comments",
            "answer.down_vote_count",
            "answer.last_editor",
            "answer.link",
            "answer.share_link",
            "answer.up_vote_count",
            "comment.body",
            "comment.body_markdown",
            "comment.link",
            "question.answers",
            "question.body",
            "question.body_markdown",
            "question.comment_count",
            "question.comments",
            "question.down_vote_count",
            "question.favorite_count",
            "question.last_editor",
            "question.notice",
            "question.share_link",
            "question.up_vote_count"
        ]
        filter_string = v2client.create_filter(filter_attributes)
    else:  # Stack Overflow Business or Basic
        filter_string = '!X9DEEiFwy0OeSWoJzb.QMqab2wPSk.X2opZDa2L'
    questions = v2client.get_all_questions(filter_string)

    return questions


def get_articles(v2client):

    if v2client.soe:
        filter_attributes = [
            "article.body",
            "article.body_markdown",
            "article.comment_count",
            "article.comments",
            "article.last_editor",
            "comment.body",
            "comment.body_markdown",
            "comment.link"
        ]
        filter_string = v2client.create_filter(filter_attributes)
    else:  # Stack Overflow Business or Basic
        filter_string = '!*Mg4Pjg9LXr9d_(v'

    articles = v2client.get_all_articles(filter_string)

    return articles


def get_tags(v3client):

    # While API v2 is more robust for collecting tag data, it does not return the tag ID field,
    # which is needed to get the SMEs for each tag. Therefore, API v3 is used to get the tag ID
    tags = v3client.get_tags()

    # Get subject matter experts (SMEs) for each tag. This API call is only available in v3.
    # There's no way to get SME configurations in bulk, so this call must be made for each tag,
    # making it a bit slower to get through.
    # FUTURE WORK: implementing some form of concurrency would speed this up.
    for tag in tags:
        if tag['subjectMatterExpertCount'] > 0:
            tag['smes'] = v3client.get_tag_smes(tag['id'])
        else:
            tag['smes'] = {'users': [], 'userGroups': []}

    return tags


def get_users(v2client, v3client):

    # Filter documentation: https://api.stackexchange.com/docs/filters
    if 'soedemo' in v2client.api_url:  # for internal testing
        filter_string = ''
    elif v2client.soe:  # Stack Overflow Enterprise requires the generation of a custom filter
        filter_attributes = [
            "user.is_deactivated"  # this attribute is only available in Enterprise and in API v2
        ]
        filter_string = v2client.create_filter(filter_attributes)
    else:  # Stack Overflow Business or Basic
        filter_string = ''

    v2_users = v2client.get_all_users(filter_string)

    # Exclude users with an ID of less than 1 (i.e. Community user and user groups)
    v2_users = [user for user in v2_users if user['user_id'] > 1]

    if 'soedemo' in v3client.api_url:  # for internal testing only
        v2_users = [user for user in v2_users if user['user_id'] > 28000]

    v3_users = v3client.get_users()

    # Add additional user data from API v3 to user data from API v2
    # API v3 fields to add: 'email', 'jobTitle', 'department', 'externalId, 'role'
    for user in v2_users:
        for v3_user in v3_users:
            if user['user_id'] == v3_user['id']:
                user['email'] = v3_user['email']
                user['title'] = v3_user['jobTitle']
                user['department'] = v3_user['department']
                user['external_id'] = v3_user['externalId']
                if v3_user['role'] == 'Moderator':
                    user['moderator'] = True
                else:
                    user['moderator'] = False
                break
        try:
            user['moderator']
        except KeyError:  # if user is not found in v3 data, it means they're a deactivated user
            # API v3 data can be obtained for deactivated users; it requires a separate API call
            v3_user = v3client.get_user_by_id(user['user_id'])
            user['email'] = v3_user['email']
            user['title'] = v3_user['jobTitle']
            user['department'] = v3_user['department']
            user['external_id'] = v3_user['externalId']
            user['is_deactivated'] = True

            if v3_user['role'] == 'Moderator':
                user['moderator'] = True
            else:
                user['moderator'] = False

    return v2_users


def get_reputation_history(v2client, users):

    user_ids = [user['user_id'] for user in users]
    reputation_history = v2client.get_reputation_history(user_ids)

    return reputation_history


def get_user_groups(v3client):

    user_groups = v3client.get_user_groups()
    return user_groups


def get_communities(v3client):

    communities = v3client.get_communities()
    return communities


def get_collections(v3client):

    collections = v3client.get_collections()
    return collections


if __name__ == "__main__":
    collector()
