# -*- coding: utf-8 -*-
"""
this is the file that runs EVERY night at 10:00 PM EST to pull in new Covid data and build predictions
from it
"""
import pandas as pd
from fbprophet import Prophet
import numpy as np
from pandas import DataFrame

def build_prophet_preds(data_url: str, 
                        changepoint_scale: float, 
                        holidays_scale: float,
                        seasonality_scale: float,
                        growth ='logistic') -> DataFrame:
    
    """
    Connects to Covid Data API, fits Prophet model on top level # of cases, and projects down to all 50
       states.  
       
    Arguments:
        data_url:          str,   url to use to connect to data
        changepoint_scale: float, number to use in prophet model for changepoint_prior_scale argument
        holidays_scale:    float, number to use in prophet model for holidays_prior_scale argument
        seasonality_scale: float, number to use in prophet model for holidays_prior_scale_argument
        growth:            str,   what type of trend growth to use.  Should be one of ['logistic', 'linear']
        
    Returns:
        test_df: a 57 X 29 DataFrame with predictions for all 56 US Territories + USA (total) that contains 
        columns that denote prediction, .975 percentile prediction, .025 percentile prediction, and date for \
        each of the following 7 days from most recent date in dataset"""

    # read in the data
    df = pd.read_csv(data_url, parse_dates=['date'])
    
    ### PART 1: USE PROPHET TO FIT TOP-LEVEL FORECAST ON ALL CASES
    
    # get total number of cases for each day
    cases = df.groupby('date')['positiveIncrease'].sum().reset_index()
    cases.rename({'date': 'ds', 'positiveIncrease': 'y'}, axis=1, inplace=True)
    
    # variables we'll use a few times
    cap   = 1000000
    floor = 0
    
    # add cap + floor for logistic growth model
    cases['cap'] = cap
    cases['floor'] = floor
    
    # initialize -- parameters were set via cross validation -- see notebook for covid modeling for more detail
    mod = Prophet(growth='logistic',
                  changepoint_prior_scale = changepoint_scale,
                  holidays_prior_scale    = holidays_scale,
                  seasonality_prior_scale = seasonality_scale)
    
    mod.add_country_holidays(country_name='US')
    
    print(f"Fitting Model with parameters: changepoint_scale = {mod.changepoint_prior_scale}, holidays_scale: {mod.holidays_prior_scale}, seasonality_scale: {mod.seasonality_prior_scale}")
    mod.fit(cases)
    
    # make df for future predictions -- seven days from most recent date in data set 
    dates           = pd.date_range(df['date'].max() + pd.DateOffset(days=1), periods=7).tolist()
    df_vals         = [(date, cap, floor) for date in dates]
    future          = pd.DataFrame(df_vals, columns=['ds', 'cap', 'floor'])
    
    # get top level predictions for each day in our forecast
    top_level_preds = mod.predict(future)[['ds', 'yhat', 'yhat_upper', 'yhat_lower']]
    
    ### PART 2: PROJECT TOP LEVEL PREDICTIONS DOWN TO ALL 50 STATES!
    
    # create new df with date/state pairs for each state and date for forecast dates
    states       = df['state'].unique().tolist()
    test_df_vals = [(date, state) for date in dates for state in states]
    test_df      = pd.DataFrame(test_df_vals, columns=['date', 'state']).sort_values(by='date')
    
    # get 7 day moving average of proportions for each state in our dataset, as of last day of recorded data
    train_grp        = df.groupby('date')['positiveIncrease'].sum()
    train_cases      = df.merge(train_grp, on='date', how='left')
    train_cases.rename({'positiveIncrease_y': 'totalCases'}, axis=1, inplace=True)
    train_cases['proportion'] = train_cases['positiveIncrease_x'] / train_cases['totalCases']
    train_cases.set_index(['state', 'date'], inplace=True)
    train_cases.sort_index(level=[0, 1], inplace=True)
    prop_moving_avgs = train_cases.groupby(level=0)['proportion'].rolling(7).mean()
    final_props      = prop_moving_avgs.groupby(level=0).last()
    
    # merge proportions w/ preds_df on each unique date, proportion values
    test_df = test_df.merge(final_props, left_on='state', right_index=True, how='left')
    test_df = test_df.merge(top_level_preds, left_on='date', right_on='ds', how='left')
    test_df.dropna(inplace=True)
    
    # this loop takes each of our top level forecasted values, and multiplies them by the proportion
    # for each state on each day
    for col in ['yhat', 'yhat_upper', 'yhat_lower']:
        test_df[col] = test_df['proportion'] * test_df[col]
        
    # don't need these columns
    test_df.drop(['ds', 'proportion'], axis=1, inplace=True)
    
    # re-organize df to get a column for upper, lower, middle prediction for each state on each day
    test_df = test_df.pivot(index='state', columns='date', values=['yhat', 'yhat_upper', 'yhat_lower'])
    
    # following lines are to format test_df to something more readable in the database
    
    # get unique dates in test_df, in ascending order
    times   = sorted(list(set(time for label, time in test_df.columns if 'yhat' in label)))
    # rename test_df columns to make them more semantic
    columns = [f'day{i}_{ending}' for ending in ['pred', 'pred_upper', 'pred_lower'] for i in range(1, len(times) + 1)]
    test_df.columns = columns
    
    # note what date day 1, 2, 3, etc actually are
    for idx, time in enumerate(times, start=1):
        test_df[f"day{idx}_date"] = time
        
    # popout out the state index one more time
    test_df.reset_index(inplace=True)
    
    # these last lines add a final line to test_df for total values for the entire usa
    num_vals   = test_df.select_dtypes(include=np.number).sum()
    time_vals  = test_df.select_dtypes(include=np.datetime64).iloc[0]
    index_vals = num_vals.index.tolist() + time_vals.index.tolist()
    index_vals.insert(0, 'state')
    
    series_vals = num_vals.tolist() + time_vals.tolist()
    series_vals.insert(0, 'USA')
    
    test_df = test_df.append(pd.Series(series_vals,  index=index_vals), ignore_index=True)
    test_df['model'] = 'Prophet'
    
    return test_df

