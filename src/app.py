"""
Main application file for dashboard!
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from utils import develop_tick_marks, convert_to_int, create_connection_string
import dash_bootstrap_components as dbc
from sqlalchemy import create_engine
import pickle
import os

# this initializes the application
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE])

# we'll load in our data here at the very beginning
data = pd.read_csv('https://api.covidtracking.com/v1/states/daily.csv', parse_dates=['date'])
data.sort_values(by='date', inplace=True)

# load in our connection info
# setup absolute file directory paths -- necessary for servers
script_directory = os.path.dirname(os.path.abspath(__file__))
data_file        = os.path.join(script_directory, "info.pkl")
with open(data_file, 'rb') as info:
    connection_info = pickle.load(info)

connection_string = create_connection_string(connection_info)

engine            = create_engine(connection_string)

# and get our database info
with engine.connect() as connection:
    db_df = pd.read_sql_query('SELECT * FROM jonathanbechtel$covid.predictions ORDER BY dt DESC LIMIT 57', con=connection)

# Global Variables That Will Be Used Throughout App
dcc_options = [{'label': 'New Cases', 'value': 'positiveIncrease'},
               {'label': 'New Hospitalizations', 'value': 'hospitalizedIncrease'},
               {'label': 'New Deaths', 'value': 'deathIncrease'},
               {'label': 'New Tests', 'value': 'totalTestResultsIncrease'}]

dcc_mapping = {'positiveIncrease': 'positive',
               'hospitalizedIncrease': 'hospitalized',
               'deathIncrease': 'death',
               'totalTestResultsIncrease': 'totalTestResults'}


# this is where you specify how the application will render itself
app.layout = dbc.Container(id='main-container',
             children=[html.Div(children=[
             html.Br(),
             html.Br(),
             html.H2("Daily Covid19 Case Count Forecasts"),
             html.Hr(),
             dbc.Label(["Choose A State To Get Its 7 Day Forecast",
             dcc.Dropdown(id='forecast-dropdown', options=[{'label': i, 'value': i} for i in db_df['state'].unique()], value='USA', clearable=False)]),
             html.Hr(),
             html.H3(id="forecast-title"),
             html.Div(id="forecast-container"),
             html.Hr(),
             html.H4("Visual Metric Explorer"),
             dbc.Row([
                dbc.Col(dbc.Label(["Choose A Metric To See Its State by State Breakdown -- Click on a State To See Its Specific Info To the Right", dcc.Dropdown(id='metric-dropdown', options=dcc_options, value='positiveIncrease', clearable=False)]), width=7),
                dbc.Col(dcc.Checklist(id='cumulative',
                        options=[
                                {'label': 'Cumulative', 'value': True}
                                ],
                        value=[True]
                ),width=2)
            ]),
            dbc.Row([
                  dbc.Col(dcc.Graph(id='main-chart'), width=9),
                  dbc.Col(dcc.Graph(id='output'), width=3)
            ]),

             dcc.Slider(id    = 'single-date-slider',
                        min   = convert_to_int(data['date'].min()),
                        max   = convert_to_int(data['date'].max()),
                        value = convert_to_int(data['date'].max()),
                        step  = 2592000,
                        marks = develop_tick_marks('day', data['date'].min(), data['date'].max(), interval=30)),
            html.Hr(),
            html.Footer([html.Span("Created By: "), html.A("Jonathan Bechtel", href="https://www.jonathanbech.tel"),
                         html.Span("   Data Created From Covid Tracking Project: "), html.A("Data Source", href="https://covidtracking.com/data/api")])
        ])])

### CALLBACKS

### Cross Filter For Choropleth Map
@app.callback(Output('main-chart', 'figure'),
              [Input('metric-dropdown', 'value'),
               Input('single-date-slider', 'marks'),
               Input('single-date-slider', 'value'),
               Input('cumulative', 'value')])
def show_output(dropdown_val, marks, time_val, cumulative):
    date   = marks[str(time_val)]
    query  = data.date == date

    if cumulative:
        dropdown_val = dcc_mapping[dropdown_val]
        vals         = data.loc[query, ['state', dropdown_val]]
    else:
        vals   = data.loc[query, ['state', dropdown_val]]
    title      = f"Daily Totals For Metric: {dropdown_val}, on Day: {date}"
    figure     = px.choropleth(vals,
                           locations='state',
                           locationmode='USA-states',
                           scope='usa',
                           color_continuous_scale='spectral',
                           color=dropdown_val,
                           title=title)
    figure.update_layout(geo=dict(bgcolor= 'rgba(0,0,0,0)'),
        paper_bgcolor = 'rgba(0,0,0,0)',
        plot_bgcolor  = 'rgba(0,0,0,0)',
        font_color    = '#AAAAAA')
    return figure

@app.callback(Output('output', 'figure'),
              [Input('main-chart', 'clickData'),
               Input('single-date-slider', 'marks'),
               Input('single-date-slider', 'value'),
               Input('cumulative', 'value')])
def render_data(clickData, marks, time_val, cumulative):
    date = marks[str(time_val)]
    if clickData is None:
        query = data.date == date
        vals  = data.loc[query, :]
        vals_for_table = [date, 'All of US', cumulative, vals['positive'].sum(), vals['totalTestResults'].sum(), vals['death'].sum(), vals['hospitalizedCumulative'].sum(), vals['positive'].sum() / vals['totalTestResults'].sum()]
        figure = go.Figure(data=[go.Table(
            header=dict(values=['Metric', 'Value'],
            fill_color='paleturquoise',
            align='left'),
            cells=dict(values=[['Date', 'State', 'Cumulative', 'Cases', 'Tests', 'Deaths', 'Hospitalizations', '% Positive'], vals_for_table],
            fill_color='lavender',
            align='left',
            ))])
        figure.update_layout(paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor = 'rgba(0,0,0,0)',
        width = 350)
        return figure
    else:
        state = clickData['points'][0]['location']
        query = (data.state == state) & (data.date == date)
    vals  = data.loc[query, :]
    if cumulative:
        cumulative = True
        vals_for_table = [date, state, cumulative, vals['positive'], vals['totalTestResults'], vals['death'], vals['hospitalizedCumulative'], vals['positive'] / vals['totalTestResults']]
    else:
        cumulative = False
        vals_for_table = [date, state, cumulative, vals['positiveIncrease'], vals['totalTestResultsIncrease'], vals['deathIncrease'], vals['hospitalizedIncrease'], vals['positiveIncrease'] / vals['totalTestResultsIncrease']]

    figure =  go.Figure(data=[go.Table(
            header=dict(values=['Metric', 'Value'],
            fill_color='paleturquoise',
            align='left'),
            cells=dict(values=[['Date', 'State', 'Cumulative', 'Cases', 'Tests', 'Deaths', 'Hospitalizations', '% Positive'],
                               vals_for_table],
            fill_color='lavender',
            align='left'))
            ])

    figure.update_layout(geo=dict(bgcolor= 'rgba(0,0,0,0)'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        width=350)

    return figure

@app.callback([Output('forecast-container', 'children'), Output('forecast-title', 'children')],
              [Input('forecast-dropdown', 'value')])
def create_forecast_data(forecast_location):
    query       = db_df.state == forecast_location
    forecast_df = db_df.loc[query, :]
    results     = []
    for i in range(1, 8):
        forecast_pred  = forecast_df[f'day{i}_pred'].values[0]
        forecast_upper = forecast_df[f'day{i}_pred_upper'].values[0]
        forecast_lower = forecast_df[f'day{i}_pred_lower'].values[0]
        date_col       = f"day{i}_date"
        date_val       = forecast_df[date_col].values[0]
        print(date_val)
        card           = dbc.Card([dbc.CardHeader(f"{date_val}"),
                                   dbc.CardBody([html.H5(f"{forecast_pred:,}", className='card-title'),
                                                 html.P(f"{forecast_lower:,} - {forecast_upper:,}", className='card-text')])
                                   ])
        results.append(card)
    return dbc.CardGroup(results), f"7 Day Forecast for {forecast_location} Covid Cases"
