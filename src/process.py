# -*- coding: utf-8 -*-
"""
This file is designed to organize all the different subroutines needed to make the application work
on a daily basis
"""
import pickle
from utils import build_prophet_preds, add_to_db

# load in db info
with open('info.pkl', 'rb') as info:
    db_info = pickle.load(info)
    
connection_string = f"{db_info['driver']://{db_info['username']}:{db_info['password']}@{db_info['host']}/{db_info['database']}"


data_url          = 'https://api.covidtracking.com/v1/states/daily.csv'
changepoint_scale = 0.7
seasonality_scale = 10
holidays_scale    = 10

preds = build_prophet_preds(data_url, changepoint_scale, holidays_scale, seasonality_scale)

try:
    add_to_db(preds, 'predictions', connection_string)
except Exception as e:
    print(f"Could not add anything to database because: {e}")