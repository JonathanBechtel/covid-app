"""
This file is designed to organize all the different subroutines needed to make the application work
on a daily basis
"""
import pickle
from utils import add_to_db
from model import build_prophet_preds
import os

# setup absolute file directory paths
script_directory = os.path.dirname(os.path.abspath(__file__))
data_file        = os.path.join(script_directory, "info.pkl")

# load in db info
with open(data_file, 'rb') as info:
    db_info = pickle.load(info)

connection_string = f"{db_info['driver']}://{db_info['username']}:{db_info['password']}@{db_info['host']}:{db_info['port']}/{db_info['database']}"


data_url          = 'https://api.covidtracking.com/v1/states/daily.csv'
changepoint_scale = 0.7
seasonality_scale = 10
holidays_scale    = 10

preds = build_prophet_preds(data_url, changepoint_scale, holidays_scale, seasonality_scale)

try:
    add_to_db(preds, 'predictions', connection_string)
except Exception as e:
    print(f"Could not add anything to database because: {e}")