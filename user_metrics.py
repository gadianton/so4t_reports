# Standard Python libraries
import time
import statistics


def create_user_metrics(users, questions, articles, tags):

    users = add_new_user_fields(users)
    users = process_tags(users, tags)
    users = process_questions(users, questions)
    users = process_articles(users, articles)
    # users = process_reputation_history(users, api_data['reputation_history'])
    users = process_users(users)

    # Create a list of user dictionaries, sorted by net reputation
    sorted_users = sorted(users, key=lambda k: k['reputation'], reverse=True)

    # Select fields for the user report
    user_metrics = []
    for user in sorted_users:
        try:
            user_metric = {
                'User ID': user['user_id'],
                'Display Name': user['display_name'],
                'Reputation': user['reputation'],
                'Account Longevity (Days)': user['account_longevity_days'],
                'Account Inactivity (Days)': user['account_inactivity_days'],

                'Questions': user['question_count'],
                'Questions With No Answers': user['questions_with_no_answers'],
                # 'Question Upvotes': user['question_upvotes'],
                # 'Question Downvotes': user['question_downvotes'],

                'Answers': user['answer_count'],
                # 'Answer Upvotes': user['answer_upvotes'],
                # 'Answer Downvotes': user['answer_downvotes'],
                'Answers Accepted': user['answers_accepted'],
                'Median Answer Time (Hours)': user['answer_response_time_median'],

                'Articles': user['article_count'],
                # 'Article Upvotes': user['article_upvotes'],

                'Comments': user['comment_count'],

                'Total Upvotes': user['total_upvotes'],
                'Total Downvotes': user['total_downvotes'],

                # 'Searches': user['searches'],
                # 'Communities': user['communities'],
                'SME Tags': ', '.join(user['sme_tags']),
                # 'Watched Tags': user['watched_tags'],

                'Account Status': user['account_status'],
                'Moderator': user['moderator'],

                'Email': user['email'],
                'Title': user['title'],
                'Department': user['department'],
                'External ID': user['external_id'],
                'Account ID': user['account_id']
            }
        except KeyError as e:
            print(f"KeyError: missing [{e.args[0]}] key for user {user['user_id']}")
            print(f"Link to user: {user.get('link')}")
            print("Data for this user will not be included in the report.")
            print("\n")
            input("Press Enter to continue...")
            continue
        user_metrics.append(user_metric)

    return user_metrics


def add_new_user_fields(users):

    for user in users:
        user['questions'] = []
        user['question_count'] = 0
        user['questions_with_no_answers'] = 0
        user['question_upvotes'] = 0
        user['question_downvotes'] = 0

        user['answers'] = []
        user['answer_count'] = 0
        user['answer_upvotes'] = 0
        user['answer_downvotes'] = 0
        user['answers_accepted'] = 0
        user['answer_response_times'] = []
        user['answer_response_time_median'] = 0

        user['articles'] = []
        user['article_count'] = 0
        user['article_upvotes'] = 0

        user['comments'] = []
        user['comment_count'] = 0

        user['total_upvotes'] = 0
        user['reputation_history'] = []
        user['net_reputation'] = 0

        user['searches'] = []
        user['communities'] = []
        user['sme_tags'] = []
        user['watched_tags'] = []

        user['account_longevity_days'] = round(
            (time.time() - user['creation_date'])/60/60/24)
        user['account_inactivity_days'] = round(
            (time.time() - user['last_access_date'])/60/60/24)

        try:
            if user['is_deactivated']:
                user['account_status'] = 'Deactivated'
            else:
                user['account_status'] = 'Active'
        except KeyError:  # Stack Overflow Business or Basic
            user['account_status'] = 'Registered'
    return users


# def process_reputation_history(users, reputation_history):

#     for user in users:
#         for event in reputation_history:
#             if event['user_id'] == user['user_id']:
#                     user['reputation_history'].append(event)

#     return users


def process_tags(users, tags):
    '''
    Iterate through each tag, find the SMEs, and add the tag name to a new field
    on the user object, indicating which tags they're a SME for
    In some situations, a user may be listed as both an individual SME and a group SME
    '''
    for tag in tags:
        for user in users:
            for sme in tag['smes']['users']:
                if user['user_id'] == sme['id']:
                    user['sme_tags'].append(tag['name'])
                    continue  # if user is an individual SME, skip the group SME check
            for sme in tag['smes']['userGroups']:
                if user['user_id'] == sme['id']:
                    user['sme_tags'].append(tag['name'])

    return users


def process_questions(users, questions):

    for question in questions:
        asker_id = validate_user_id(question['owner'])
        user_index = get_user_index(users, asker_id)

        if user_index is None:  # if user was deleted, add them to the list
            deleted_user = initialize_deleted_user(asker_id, question['owner']['display_name'])
            users.append(deleted_user)
            user_index = get_user_index(users, asker_id)

        users[user_index]['questions'].append(question)

        if question.get('answers'):
            users = process_answers(users, question['answers'], question)

        if question.get('comments'):
            users = process_comments(users, question)

    return users


def process_answers(users, answers, question):

    for answer in answers:
        answerer_id = validate_user_id(answer['owner'])
        user_index = get_user_index(users, answerer_id)

        if user_index is None:
            deleted_user = initialize_deleted_user(answerer_id, answer['owner']['display_name'])
            users.append(deleted_user)
            user_index = get_user_index(users, answerer_id)

        users[user_index]['answers'].append(answer)
        answer_response_time_hours = (answer['creation_date'] - question['creation_date'])/60/60
        users[user_index]['answer_response_times'].append(answer_response_time_hours)

        if answer.get('comments'):
            users = process_comments(users, answer)

    return users


def process_comments(users, object_with_comments):

    for comment in object_with_comments['comments']:
        commenter_id = validate_user_id(comment['owner'])
        user_index = get_user_index(users, commenter_id)

        if user_index is None:
            deleted_user = initialize_deleted_user(commenter_id, comment['owner']['display_name'])
            users.append(deleted_user)
            user_index = get_user_index(users, commenter_id)

        users[user_index]['comments'].append(comment)

    return users


def process_articles(users, articles):

    for article in articles:
        author_id = validate_user_id(article['owner'])
        user_index = get_user_index(users, author_id)
        if user_index is None:
            deleted_user = initialize_deleted_user(author_id, article['owner']['display_name'])
            users.append(deleted_user)
            user_index = get_user_index(users, author_id)

        users[user_index]['articles'].append(article)

        # As of 2023.05.23, Article comments are slightly innaccurate due to a bug in the API
        # if article.get('comments'):
        #     for comment in article['comments']:
        #         commenter_id = validate_user_id(comment)
        #         tag_contributors[tag]['commenters'] = add_user_to_list(
        #             commenter_id, tag_contributors[tag]['commenters']
        #         )

    return users


def process_users(users):

    for user in users:
        for question in user['questions']:
            user['question_count'] += 1
            user['question_upvotes'] += question['up_vote_count']
            user['question_downvotes'] += question['down_vote_count']
            if question['answer_count'] == 0:
                user['questions_with_no_answers'] += 1

        for answer in user['answers']:
            user['answer_count'] += 1
            user['answer_upvotes'] += answer['up_vote_count']
            user['answer_downvotes'] += answer['down_vote_count']
            if answer['is_accepted']:
                user['answers_accepted'] += 1

        for article in user['articles']:
            user['article_count'] += 1
            user['article_upvotes'] += article['score']

        for comment in user['comments']:
            user['comment_count'] += 1

        # for event in user['reputation_history']:
        #     user['net_reputation'] += event['reputation_change']

        for answer_response_time in user['answer_response_times']:
            if answer_response_time <= 0:
                user['answer_response_times'].remove(answer_response_time)

        if user['answer_response_times']:
            user['answer_response_time_median'] = round(
                statistics.median(user['answer_response_times']), 2)
        else:
            user['answer_response_time_median'] = ''

        user['total_upvotes'] = user['question_upvotes'] + user['answer_upvotes'] + \
            user['article_upvotes']
        user['total_downvotes'] = user['question_downvotes'] + user['answer_downvotes']

    return users


def get_user_index(users, user_id):

    for index, user in enumerate(users):
        if user['user_id'] == user_id:
            return index

    return None  # if user is not found


def initialize_deleted_user(user_id, display_name):

    user = {
        'user_id': user_id,
        'display_name': f"{display_name} (DELETED)",

        'questions': [],
        'question_count': 0,
        'questions_with_no_answers': 0,
        'question_upvotes': 0,
        'question_downvotes': 0,

        'answers': [],
        'answer_count': 0,
        'answer_upvotes': 0,
        'answer_downvotes': 0,
        'answers_accepted': 0,
        'answer_response_times': [],

        'articles': [],
        'article_count': 0,
        'article_upvotes': 0,

        'comments': [],
        'comment_count': 0,

        'total_upvotes': 0,
        'reputation': 0,
        'reputation_history': [],
        'net_reputation': 0,

        'searches': [],
        'communities': [],
        'sme_tags': [],
        'watched_tags': [],

        'moderator': '',
        'email': '',
        'title': '',
        'department': '',
        'external_id': '',
        'account_id': '',
        'account_longevity_days': '',
        'account_inactivity_days': '',
        'account_status': 'Deleted'
    }

    return user


def validate_user_id(user):
    """
    Checks to see if a user_id is present. If not, the user has been deleted. In this case, the
    user_id can be extracted from the display_name. For example, if a deleted user's display_name
    is 'user123', the user_id will be 123."""

    try:
        user_id = user['user_id']
    except KeyError:  # if user_id is not present, the user was deleted
        try:
            user_id = int(user['display_name'].split('user')[1])
        except IndexError:
            # This shouldn't happen, but if it does, the user_id will be the display name
            # This seems to only happen in the internal testing environment
            user_id = user['display_name']

    return user_id


# def export_to_csv(data_name, data):

#     date = time.strftime("%Y-%m-%d")
#     file_name = f"{date}_{data_name}.csv"

#     csv_header = [header for header in list(data[0].keys())]
#     with open(file_name, 'w', encoding='UTF8', newline='') as f:
#         writer = csv.writer(f)
#         writer.writerow(csv_header)
#         for tag_data in data:
#             writer.writerow(list(tag_data.values()))

#     print(f'CSV file created: {file_name}')
