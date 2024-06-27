from datetime import datetime
from dateutil.relativedelta import relativedelta


def create_kr_metrics(questions, articles):

    date_filters = create_date_filters()
    kr_metrics = []
    for filter_name, filter in date_filters.items():

        filtered_questions = filter_content_by_date(questions, filter)
        filtered_articles = filter_content_by_date(articles, filter)

        total_page_views = 0
        deleted_page_views = 0
        for question in filtered_questions:
            total_page_views += question['view_count']
            if not question['owner'].get('user_id'):
                deleted_page_views += question['view_count']
                continue  # don't count page views of answers if question is already counted
            if question.get('answers'):
                for answer in question['answers']:
                    if not answer['owner'].get('user_id'):
                        deleted_page_views += question['view_count']
                        # don't count page views of subsequent answers (i.e. avoid duplication)
                        break

        for article in filtered_articles:
            total_page_views += article['view_count']
            if not article['owner'].get('user_id'):
                deleted_page_views += article['view_count']
        try:
            page_view_percentage = "{:.2f}".format((deleted_page_views / total_page_views) * 100)
        except ZeroDivisionError:
            page_view_percentage = 0
        filter_data = {
            "Time Frame": filter_name,
            "Page Views of Content Created During Time Frame": total_page_views,
            "Page Views of Content Created by Users Now Deleted": deleted_page_views,
            "Percent of Knowledge Reuse Attributed to Deleted Users": page_view_percentage
        }
        kr_metrics.append(filter_data)

    return kr_metrics


def create_date_filters():

    now = datetime.now()
    date_filters = {
        'Past Month': now - relativedelta(months=1),
        'Past Quarter': now - relativedelta(months=3),
        'Past Six Months': now - relativedelta(months=6),
        'Past Year': now - relativedelta(years=1),
        'Past Two Years': now - relativedelta(years=2),
        'All Time': now - relativedelta(years=100)
    }
    return date_filters


def convert_timestamp_format(timestamp):
    return datetime.fromtimestamp(timestamp)


def filter_content_by_date(content_pieces, date_filter):
    filtered_content = []
    for content in content_pieces:
        content_ts = convert_timestamp_format(content['creation_date'])
        if content_ts > date_filter:
            filtered_content.append(content)

    return filtered_content
