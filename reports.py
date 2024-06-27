# Native Python libraries
import csv
import json
import logging
from math import sqrt
import os

# Third-party libraries
import pandas as pd
import plotly.graph_objs as go
import plotly.offline as pyo
from plotly.subplots import make_subplots
from wordcloud import WordCloud

# Local libraries
from collector import DATA_DIR
from tag_metrics import create_tag_metrics
from user_metrics import create_user_metrics
from knowledge_reuse_metrics import create_kr_metrics

REPORT_DIR = 'reports'


def create_reports():

    # Read data from JSON files
    questions = read_json('questions', DATA_DIR)
    articles = read_json('articles', DATA_DIR)
    tags = read_json('tags', DATA_DIR)
    users = read_json('users', DATA_DIR)
    communities = read_json('communities', DATA_DIR)

    # Calculate tag metrics and store them in a new collection
    tag_metrics = create_tag_metrics(questions, articles, tags, communities)
    export_to_json('tag_metrics', tag_metrics)

    # Calculate user metrics and store them in a new collection
    user_metrics = create_user_metrics(users, questions, articles, tags)
    export_to_json('user_metrics', user_metrics)

    # Calculate knowledge reuse (kr) metrics and store them in a new collection
    kr_metrics = create_kr_metrics(questions, articles)
    export_to_json('kr_metrics', kr_metrics)

    # CSV reports
    export_to_csv('tag_report', tag_metrics)
    export_to_csv('user_report', user_metrics)
    create_deleted_user_kr_csv(kr_metrics)

    # Graphical reports
    create_tag_cloud(tag_metrics)
    create_tag_charts(tag_metrics)
    create_department_charts(user_metrics)


def create_tag_cloud(tag_metrics, max_tags=100):

    # The wordcloud library is expecting a dictionary of dictionaries
    # df = pd.DataFrame(tag_metrics)
    # df = df[['tag_name', 'total_page_views']]
    # dict_data = df.to_dict('records')
    # wordcloud_data = {item['tag_name']: item['total_page_views'] for item in dict_data}
    wordcloud_data = {item['tag_name']: item['total_page_views'] for item in tag_metrics}

    wordcloud = WordCloud(
        width=1600,
        height=900,
        max_words=max_tags,
        background_color='white')

    wordcloud.generate_from_frequencies(wordcloud_data)

    file_name = f'so4t_tag_cloud_{max_tags}_tags.png'
    file_path = os.path.join(REPORT_DIR, file_name)
    wordcloud.to_file(file_path)
    logging.info(f'Tag cloud image saved to {file_path}')


def create_deleted_user_kr_csv(kr_metrics):

    fieldnames = [k for k in kr_metrics[0].keys()]
    file_name = 'deleted_kr.csv'
    file_path = os.path.join(REPORT_DIR, file_name)
    with open(file_path, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kr_metrics)


def create_tag_charts(tag_metrics):

    create_tag_bubble_chart(tag_metrics)
    create_tag_sme_chart(tag_metrics)
    create_tag_watcher_chart(tag_metrics)


def create_tag_bubble_chart(tag_metrics):

    for tag in tag_metrics:
        try:
            answer_percentage = tag['questions_no_answers'] / tag['question_count']
            tag['answer_percentage'] = round((1 - answer_percentage) * 100, 1)
        except ZeroDivisionError:
            tag['answer_percentage'] = 0

    tag_metrics = [tag for tag in tag_metrics if tag['question_count'] > 1]
    tag_metrics = [tag for tag in tag_metrics if tag['median_time_to_first_answer_hours'] < 100]
    tag_metrics = [tag for tag in tag_metrics if tag['answer_percentage'] > 0]

    x_values = [tag['answer_percentage'] for tag in tag_metrics]
    y_values = [tag['median_time_to_first_answer_hours'] for tag in tag_metrics]

    # Using sqrt to scale the bubble sizes more appropriately
    sizes = [sqrt(tag['question_count']) for tag in tag_metrics]
    tooltips = [
        f"Tag: {d['tag_name']}<br>"
        f"Total Page Views: {d['total_page_views']}<br>"
        f"Question Count: {d['question_count']}<br>"
        f"Answer %: {d['answer_percentage']}<br>"
        f"Median Time to First Answer: {d['median_time_to_first_answer_hours']}<br>"
        f"SMEs: {d['total_smes']}<br>"
        f"Tag Watchers: {d['tag_watchers']}"
        for d in tag_metrics
    ]

    trace = go.Scatter(
        x=x_values,
        y=y_values,
        mode='markers',
        marker=dict(
            size=sizes,
            sizemode='area',
            sizeref=2.*max(sizes)/(40.**2),
            sizemin=4
        ),
        text=tooltips,
        name=''
    )

    layout = go.Layout(
        title='Tag Health',
        xaxis=dict(title='Answer Percentage'),
        yaxis=dict(title='Median Time to First Answer (Hours)',
                   autorange='reversed'),
        hovermode='closest'
    )

    data = [trace]
    fig = go.Figure(data=data, layout=layout)
    pyo.plot(fig, filename=f'{REPORT_DIR}/tag_bubble_chart.html')


def create_tag_sme_chart(tag_metrics):

    smes = {
        '0': 0,
        '1-2': 0,
        '3-5': 0,
        '6-10': 0,
        '11-20': 0,
        '20+': 0
    }

    for tag in tag_metrics:
        if tag['total_smes'] == 0:
            smes['0'] += 1
        elif tag['total_smes'] < 3:
            smes['1-2'] += 1
        elif tag['total_smes'] < 6:
            smes['3-5'] += 1
        elif tag['total_smes'] < 11:
            smes['6-10'] += 1
        elif tag['total_smes'] < 21:
            smes['11-20'] += 1
        else:
            smes['20+'] += 1

    x_values = list(smes.keys())
    y_values = list(smes.values())

    trace = go.Bar(
        x=x_values,
        y=y_values,
        hovertemplate='Tags with %{label} SMEs: %{value}',
        texttemplate='Tags w/ %{label} SMEs: %{value}',
        textposition='outside',
        name=''
    )

    layout = go.Layout(
        title='SME Count',
        xaxis=dict(title='SME Count'),
        yaxis=dict(title='Tag Count'),
    )

    data = [trace]
    fig = go.Figure(data=data, layout=layout)
    pyo.plot(fig, filename=f'{REPORT_DIR}/sme_count_chart.html')


def create_tag_watcher_chart(tag_metrics):

    tag_watchers = {
        '0': 0,
        '1-2': 0,
        '3-5': 0,
        '6-10': 0,
        '11-20': 0,
        '20+': 0
    }

    for tag in tag_metrics:
        if tag['tag_watchers'] == 0:
            tag_watchers['0'] += 1
        elif tag['tag_watchers'] < 3:
            tag_watchers['1-2'] += 1
        elif tag['tag_watchers'] < 6:
            tag_watchers['3-5'] += 1
        elif tag['tag_watchers'] < 11:
            tag_watchers['6-10'] += 1
        elif tag['tag_watchers'] < 21:
            tag_watchers['11-20'] += 1
        else:
            tag_watchers['20+'] += 1

    x_values = list(tag_watchers.keys())
    y_values = list(tag_watchers.values())

    trace = go.Bar(
        x=x_values,
        y=y_values,
        hovertemplate='Tags with %{label} watchers: %{value}',
        texttemplate='Tags w/ %{label} watchers: %{value}',
        textposition='outside',
        name=''
    )

    layout = go.Layout(
        title='Tag Watchers',
        xaxis=dict(title='Tag Watchers'),
        yaxis=dict(title='Tag Count')
    )

    data = [trace]
    fig = go.Figure(data=data, layout=layout)
    pyo.plot(fig, filename=f'{REPORT_DIR}/tag_watcher_chart.html')


def create_department_charts(user_metrics):

    # Remove users where "Account Status" is "Deleted"
    user_metrics = [user for user in user_metrics if user['Account Status'] != 'Deleted']

    # If no department is available, set to "Unknown"
    for user in user_metrics:
        if not user.get('Department'):
            user['Department'] = 'Unknown'

    department_metrics = {}
    for user in user_metrics:
        department = user['Department']
        if department in department_metrics:
            department_metrics[department]['User Count'] += 1
            department_metrics[department]['Question Count'] += user['Questions']
            department_metrics[department]['Answer Count'] += user['Answers']
        else:
            department_metrics[department] = {
                'User Count': 1,
                'Question Count': user['Questions'],
                'Answer Count': user['Answers']
            }

    # Sort dictionary by user count
    department_metrics = dict(sorted(department_metrics.items(),
                                     key=lambda item: item[1]['User Count'],
                                     reverse=True))

    # Calculate average questions and answers per user per department

    # Create dictionary for each chart
    department_users = {department: metrics['User Count'] for department, metrics
                        in department_metrics.items()}
    department_questions = {department: metrics['Question Count'] for department, metrics
                            in department_metrics.items()}
    department_answers = {department: metrics['Answer Count'] for department, metrics
                          in department_metrics.items()}

    # Documentation for make_subplots: https://plotly.com/python/subplots/
    fig = make_subplots(
        rows=2, cols=3,
        start_cell="top-left",
        specs=[
            [{"type": "pie"}, {"type": "pie"}, {"type": "pie"}],
            [{"type": "table", "colspan": 3}, None, None]
        ],
        subplot_titles=('User Count by Department',
                        'Question Count by Department',
                        'Answer Count by Department')

    )

    # Create pie chart for user count by department
    # Documentation for go.Pie: https://plotly.com/python/pie-charts/
    fig.add_trace(
        go.Pie(
            labels=list(department_users.keys()),
            values=list(department_users.values()),
            hovertemplate='%{value} users in %{label}',
            textposition='inside',
            textinfo='percent',
            name=''
        ),
        row=1, col=1
    )

    # Create pie chart for question count by department
    # Documentation for go.Pie: https://plotly.com/python/pie-charts/
    fig.add_trace(
        go.Pie(
            labels=list(department_questions.keys()),
            values=list(department_questions.values()),
            hovertemplate='%{value} questions from %{label}',
            textposition='inside',
            textinfo='percent',
            name=''
        ),
        row=1, col=2
    )

    # Create pie chart for answer count by department
    # Documentation for go.Pie: https://plotly.com/python/pie-charts/
    fig.add_trace(
        go.Pie(
            labels=list(department_answers.keys()),
            values=list(department_answers.values()),
            hovertemplate='%{value} answers from %{label}',
            textposition='inside',
            textinfo='percent',
            name=''
        ),
        row=1, col=3
    )

    # Create table for department metrics
    # Documentation for go.Table: https://plotly.com/python/table/
    fig.add_trace(
        go.Table(
            header=dict(values=['Department', 'User Count', 'Question Count', 'Answer Count']),

            cells=dict(values=[list(department_users.keys()),
                               list(department_users.values()),
                               list(department_questions.values()),
                               list(department_answers.values())]),
        ),
        row=2, col=1
    )

    fig.update_layout(
        title_text='Department Metrics',
        height=1080,
        width=1920
    )

    pyo.plot(fig, filename=f'{REPORT_DIR}/department_metrics.html')

    # create_users_department_chart(user_metrics)
    # create_questions_department_chart(user_metrics)
    # create_answers_department_chart(user_metrics)


def create_users_department_chart(user_metrics):

    departments = {}
    for user in user_metrics:
        department = user['Department']
        if department in departments:
            departments[department] += 1
        else:
            departments[department] = 1

    x_values = list(departments.keys())
    y_values = list(departments.values())

    trace = go.Pie(
        labels=x_values,
        values=y_values,
        hoverinfo='name+label+value',
        textposition='inside',
        textinfo='percent',
        name=''
    )

    layout = go.Layout(
        title='User Count by Department'
    )

    data = [trace]
    fig = go.Figure(data=data, layout=layout)
    pyo.plot(fig, filename=f'{REPORT_DIR}/user_count_by_department.html')


def create_questions_department_chart(user_metrics):

    departments = {}
    for user in user_metrics:
        department = user['Department']
        if department in departments:
            departments[department] += user['Questions']
        else:
            departments[department] = user['Questions']

    x_values = list(departments.keys())
    y_values = list(departments.values())

    trace = go.Pie(
        labels=x_values,
        values=y_values,
        hoverinfo='name+label+value',
        textposition='inside',
        textinfo='percent',
        name=''
    )

    layout = go.Layout(
        title='Question Count by Department'
    )

    data = [trace]
    fig = go.Figure(data=data, layout=layout)
    pyo.plot(fig, filename=f'{REPORT_DIR}/question_count_by_department.html')


def create_answers_department_chart(user_metrics):

    departments = {}
    for user in user_metrics:
        department = user['Department']
        if department in departments:
            departments[department] += user['Answers']
        else:
            departments[department] = user['Answers']

    x_values = list(departments.keys())
    y_values = list(departments.values())

    trace = go.Pie(
        labels=x_values,
        values=y_values,
        hoverinfo='name+label+value',
        textposition='inside',
        textinfo='percent',
        name=''
    )

    layout = go.Layout(
        title='Answer Count by Department'
    )

    data = [trace]
    fig = go.Figure(data=data, layout=layout)
    pyo.plot(fig, filename=f'{REPORT_DIR}/answer_count_by_department.html')


def export_to_csv(data_name, data):

    # Create data directory if it doesn't exist
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)

    file_name = f"{data_name}.csv"
    file_path = os.path.join(REPORT_DIR, file_name)

    csv_header = [header.replace('_', ' ').title() for header in list(data[0].keys())]
    with open(file_path, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        for tag_data in data:
            writer.writerow(list(tag_data.values()))

    print(f'CSV file created: {file_name}')


def read_json(file_name, directory=''):

    file_path = os.path.join(directory, file_name+'.json')

    try:
        with open(file_path, 'r') as f:
            data = json.loads(f.read())
    except FileNotFoundError:
        print(f'File not found: {file_path}')
        data = {}

    return data


def export_to_json(data_name, data):
    file_name = data_name + '.json'
    directory = 'data'

    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, file_name)

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
