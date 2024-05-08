# Standard Python libraries
import statistics


def create_tag_metrics(questions, articles, tags):

    tags = process_tags(tags)
    tags = process_questions(tags, questions)
    tags = process_articles(tags, articles)
    # tags = process_users(tags, api_data['users']
    # tags = process_communities(tags, api_data.get('communities'))
    # tags = process_webhooks(tags, api_data['webhooks'])

    # tally up miscellaneous metrics for each tag
    for tag in tags:
        # Calculate unique contributors
        tag['metrics']['unique_askers'] = len(tag['contributors']['askers'])
        tag['metrics']['unique_answerers'] = len(tag['contributors']['answerers'])
        tag['metrics']['unique_commenters'] = len(tag['contributors']['commenters'])
        tag['metrics']['unique_article_contributors'] = len(
            tag['contributors']['article_contributors'])
        tag['metrics']['total_unique_contributors'] = len(set(
            tag['contributors']['askers'] + 
            tag['contributors']['answerers'] +
            tag['contributors']['commenters'] + 
            tag['contributors']['article_contributors']))
        
        # Calculate total self-answered questions
        tag['metrics']['questions_self_answered'] = len(tag['self_answered_questions'])
        
        # Calculate median time to first answer and median time to first response
        try:
            tag['metrics']['median_time_to_first_response_hours'] = round(statistics.median(
                    [list(response.values())[0] for response in tag['response_times']]), 2)
        except statistics.StatisticsError: # if there are no responses for a tag
            pass
        
        try:
            tag['metrics']['median_time_to_first_answer_hours'] = round(statistics.median(
                [list(answer.values())[0] for answer in tag['answer_times']]), 2)
        except statistics.StatisticsError: # if there are no answers for a tag
            pass

        # Sort responses and answers by time to first response/answer, in descending order
        tag['response_times'] = sorted(
            tag['response_times'], 
            key=lambda k: list(k.values())[0], 
            reverse=True)
        tag['answer_times'] = sorted(
            tag['answer_times'], 
            key=lambda k: list(k.values())[0], 
            reverse=True)
    
    tag_metrics = [tag['metrics'] for tag in tags]
    tag_metrics = sorted(tag_metrics, key=lambda k: k['total_page_views'], reverse=True)
    
    return tag_metrics


def process_tags(tags):

    for tag in tags:
        tag['metrics'] = {
            'tag_name': tag['name'],
            'total_page_views': 0,
            'webhooks': 0,
            'tag_watchers': tag['watcherCount'],
            'communities': 0,
            'total_smes': 0,
            'median_time_to_first_answer_hours': 0,
            'median_time_to_first_response_hours': 0,
            'total_unique_contributors': 0,
            'unique_askers': 0,
            'unique_answerers': 0,
            'unique_commenters': 0,
            'unique_article_contributors': 0,
            'question_count': 0,
            'question_upvotes': 0,
            'question_downvotes': 0,
            'question_comments': 0,
            'questions_no_answers': 0,
            'questions_accepted_answer': 0,
            'questions_self_answered': 0,
            'answer_count': 0,
            'sme_answers': 0,
            'answer_upvotes': 0,
            'answer_downvotes': 0,
            'answer_comments': 0,
            'article_count': 0,
            'article_upvotes': 0,
            'article_comments': 0,
        }
        tag['contributors'] = {
            'askers': [],
            'answerers': [],
            'article_contributors': [],
            'commenters': [],
            'individual_smes': [],
            'group_smes': []
        }
        tag['answer_times'] = []
        tag['response_times'] = []
        tag['self_answered_questions'] = []

        # calculate total unique SMEs, including individuals and groups
        for user in tag['smes']['users']:
            tag['contributors']['individual_smes'] = add_user_to_list(
                user['id'], tag['contributors']['individual_smes'])
        for group in tag['smes']['userGroups']:
            for user in group['users']:
                tag['contributors']['group_smes'] = add_user_to_list(
                    user['id'], tag['contributors']['group_smes'])
        
        tag['metrics']['total_smes'] = len(set(
            tag['contributors']['individual_smes'] + tag['contributors']['group_smes']))
        
    return tags


def process_questions(tags, questions):

    for question in questions:
        for tag in question['tags']:
            tag_index = get_tag_index(tags, tag)
            tag_data = tags[tag_index]
            asker_id = validate_user_id(question['owner'])
            
            tag_data['contributors']['askers'] = add_user_to_list(
                asker_id, tag_data['contributors']['askers'])

            tag_data['metrics']['question_count'] += 1
            tag_data['metrics']['total_page_views'] += question['view_count']
            tag_data['metrics']['question_upvotes'] += question['up_vote_count']
            tag_data['metrics']['question_downvotes'] += question['down_vote_count']

            # Calculate tag metrics for comments
            if question.get('comments'):
                tag_data, time_to_first_comment = process_question_comments(
                    tag_data, question)
            else:
                time_to_first_comment = 0
            
            # calculate tag metrics for answers
            if question.get('answers'):
                tag_data, time_to_first_answer = process_answers(
                    tag_data, question['answers'], question)
            else:
                tag_data['metrics']['questions_no_answers'] += 1
                time_to_first_answer = 0

            # Calculate time to first response, which is the lesser of the time to first comment
            # and the time to first answer
            if time_to_first_answer > 0 and time_to_first_comment > 0:
                time_to_first_response = min(time_to_first_answer, time_to_first_comment)
            elif time_to_first_answer > 0:
                time_to_first_response = time_to_first_answer
            elif time_to_first_comment > 0:
                # If the question is self-answered, the first comment is not considered a response
                if question['link'] not in tag_data['self_answered_questions']:
                    time_to_first_response = time_to_first_comment
                else:
                    time_to_first_response = None
            else:
                time_to_first_response = None

            if time_to_first_response: # if there are no responses, don't add to list
                tag_data['response_times'].append({question['link']: time_to_first_response})
                                        
            tags[tag_index] = tag_data

    return tags

        
def process_answers(tag_data, answers, question):

    for answer in answers:
        answerer_id = validate_user_id(answer['owner'])
        tag_data['contributors']['answerers'] = add_user_to_list(
            answerer_id, tag_data['contributors']['answerers'])
        if answer['is_accepted']:
            tag_data['metrics']['questions_accepted_answer'] += 1
        tag_data['metrics']['answer_count'] += 1
        tag_data['metrics']['answer_upvotes'] += answer['up_vote_count']
        tag_data['metrics']['answer_downvotes'] += answer['down_vote_count']

        # Calculate number of answers from SMEs
        if (answerer_id in tag_data['contributors']['group_smes'] 
            or answerer_id in tag_data['contributors']['individual_smes']):
            tag_data['metrics']['sme_answers'] += 1

        if answer.get('comments'):
            tag_data['metrics']['answer_comments'] += len(answer['comments'])
            for comment in answer['comments']:
                commenter_id = validate_user_id(comment['owner'])
                tag_data['contributors']['commenters'] = add_user_to_list(
                    commenter_id, tag_data['contributors']['commenters']
                )

    # Calculate time to first answer (i.e. response) for questions
    # Deleted answers do not show up in the API response; they are not included in the calculation
        # This creates an outlier/edge case where the original answer was deleted and the next
        # fastest answer is used instead, which could've been posted at a much later time
    # If the fastest response is from the question asker, then the question is self-answered
    # If the fastest answer owner does not have a `user_id` attribute, the owner was deleted
    # If the owner of the question has a 'user_id', we can validate it was not self-answered
    # If both uers have been deleted, the `display_name` attribute can be compared to see if they
        # are the same person
    time_to_first_answer = 0
    if answers[0]['owner'].get('user_id'): # answer owner is known
        if answers[0]['owner']['user_id'] != question['owner'].get('user_id'):
            time_to_first_answer = (answers[0]['creation_date'] - question['creation_date'])/60/60
        else: # if answer owner is the same as question owner, it's a self-answer
            tag_data['self_answered_questions'].append(question['link'])
    elif question['owner'].get('user_id'): # answer owner is unknown, but question owner is known
        time_to_first_answer = (answers[0]['creation_date'] - question['creation_date'])/60/60
    else: # if both question and answer owner are unknown, check display names for a match
        if answers[0]['owner']['display_name'] == question['owner']['display_name']:
            tag_data['self_answered_questions'].append(question['link'])
        else:
            time_to_first_answer = (answers[0]['creation_date'] - question['creation_date'])/60/60

    if time_to_first_answer:
        tag_data['answer_times'].append({question['link']: time_to_first_answer})

    return tag_data, time_to_first_answer


def process_question_comments(tag_data, question):

    tag_data['metrics']['question_comments'] += len(question['comments'])
    for comment in question['comments']:
        commenter_id = validate_user_id(comment['owner'])
        tag_data['contributors']['commenters'] = add_user_to_list(
            commenter_id, tag_data['contributors']['commenters'])

    # Calculate time to first comment
    # There's an edge case where the first comment is from the question asker,
        # where we may want to consider looking at subsequent comments
        # May need to add a check for this
    # If the fastest response is from the question asker, then disregard it
    # If the fastest answer owner does not have a `user_id` attribute, the owner was deleted
    # If the owner of the question has a 'user_id', we can validate it was not self-answered
    # If both uers have been deleted, the `display_name` attribute can be compared to see if they
        # are the same person
    if question['comments'][0]['owner'].get('user_id'):
        if question['comments'][0]['owner']['user_id'] != question['owner'].get('user_id'):
            time_to_first_comment = (question['comments'][0]['creation_date'] - 
                                    question['creation_date'])/60/60
        else:
            time_to_first_comment = 0
    elif question['owner'].get('user_id'):
        time_to_first_comment = (question['comments'][0]['creation_date'] - 
                                    question['creation_date'])/60/60
    else:
        time_to_first_comment = 0

    return tag_data, time_to_first_comment


def process_articles(tags, articles):

    for article in articles:
        for tag in article['tags']:
            tag_index = get_tag_index(tags, tag)
            tag_data = tags[tag_index]
            tag_data['metrics']['total_page_views'] += article['view_count']
            tag_data['metrics']['article_count'] += 1
            tag_data['metrics']['article_upvotes'] += article['score']
            tag_data['metrics']['article_comments'] += article['comment_count']
            tag_data['metrics']['unique_article_contributors'] = len(
                tag_data['contributors']['article_contributors'])

            # Add article author to list of contributors
            article_author_id = validate_user_id(article['owner'])
            tag_data['contributors']['article_contributors'] = add_user_to_list(
                article_author_id, tag_data['contributors']['article_contributors']
            )

            # As of 2023.05.23, Article comments are slightly innaccurate due to a bug in the API
            # if article.get('comments'):
            #     for comment in article['comments']:
            #         commenter_id = validate_user_id(comment)
            #         tag_contributors[tag]['commenters'] = add_user_to_list(
            #             commenter_id, tag_contributors[tag]['commenters']
            #         )
        
            tags[tag_index] = tag_data

    return tags


def process_users(tags, users):
    ### THIS FUNCTION IS NOT CURRENTLY USED ###

    return tags


def process_communities(tags, communities):

    if communities == None: # if no communities were collected, remove the metric from the report
        for tag in tags:
            del tag['metrics']['communities']
        return tags
    
    # Search for tags in community descriptions and add community count to tag metrics
    for community in communities:
        for tag in community['tags']:
            tag_index = get_tag_index(tags, tag['name'])
            try:
                tags[tag_index]['metrics']['communities'] += 1
                try:
                    tags[tag_index]['communities'] += community
                except KeyError: # if communities key does not exist, create it
                    tags[tag_index]['communities'] = [community]
            except TypeError: # get_tag_index returned None
                pass

    return tags


def process_webhooks(tags, webhooks):

    if webhooks == None: # if no webhooks were collected, remove the metric from the report
        for tag in tags:
            del tag['metrics']['webhooks']
        return tags
    
    # Search for tags in webhook descriptions and add webhook count to tag metrics
    for webhook in webhooks:
        for tag_name in webhook['tags']:
            tag_index = get_tag_index(tags, tag_name)
            try:
                tags[tag_index]['metrics']['webhooks'] += 1
            except TypeError: # get_tag_index returned None
                pass
        
    return tags


def get_tag_index(tags, tag_name):

    for index, tag in enumerate(tags):
        if tag['name'] == tag_name:
            return index
    
    return None # if tag is not found


def add_user_to_list(user_id, user_list):
    """Checks to see if a user_id already exists is in a list. If not, it adds the new user_id to 
    the list.

    Args:
        user_id (int): the unique user ID of a particular user in Stack Overflow
        user_list (list): current user list

    Returns:
        user_list (list): updated user list
    """
    if user_id not in user_list:
        user_list.append(user_id)
    return user_list


def validate_user_id(user):

    try:
        user_id = user['user_id']
    except KeyError: # if user_id is not present, the user was deleted
        user_id = f"{user['display_name']} (DELETED)"

    return user_id


# def export_to_csv(data_name, data):

#     file_name = f"{data_name}.csv"

#     csv_header = [header.replace('_', ' ').title() for header in list(data[0].keys())]
#     with open(file_name, 'w', encoding='UTF8', newline='') as f:
#         writer = csv.writer(f)
#         writer.writerow(csv_header)
#         for tag_data in data:
#             writer.writerow(list(tag_data.values()))
        
#     print(f'CSV file created: {file_name}')



# def export_to_json(data_name, data):
    
#     file_name = data_name + '.json'
#     directory = 'data'

#     if not os.path.exists(directory):
#         os.makedirs(directory)
#     file_path = os.path.join(directory, file_name)

#     with open(file_path, 'w') as f:
#         json.dump(data, f, indent=4)

#     print(f'JSON file created: {file_name}')


# def read_json(file_name):
    
#     directory = 'data'
#     file_path = os.path.join(directory, file_name)
#     try:
#         with open(file_path, 'r') as f:
#             data = json.load(f)
#     except FileNotFoundError:
#         print(f"File not found: {file_path}")
#         raise FileNotFoundError
    
#     return data
