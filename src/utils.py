"""
helper functions to get dashboard to work better
"""
from pandas import DateOffset
from time import mktime
from pandas import DataFrame
from numpy import datetime64 as datetime
from sqlalchemy import create_engine, types


def develop_tick_marks(timepart: str, start: datetime, end: datetime, interval=1) -> dict:
    date_marks  = []
    if timepart == 'day':
        offset  = DateOffset(days=interval)
        current = end
        while current >= start:
            date_marks.append(current)
            current -= offset
        return {int(mktime(mark.timetuple())): mark.strftime('%Y-%m') for mark in date_marks[::-1]}
    
def convert_to_int(date: datetime) -> int:
    return int(mktime(date.timetuple()))

def add_to_db(df: DataFrame, table_name: str, connection_str: str) -> None:
    """Takes the dataframe returned from functions in model.py and adds it to a database using provided
    connection string"""
    dtypes = {
            'state': types.String(),
            'day1_pred': types.Integer(),
            'day2_pred': types.Integer(),
            'day3_pred': types.Integer(),
            'day4_pred': types.Integer(),
            'day5_pred': types.Integer(),
            'day6_pred': types.Integer(),
            'day7_pred': types.Integer(),
            'day1_pred_upper': types.Integer(),
            'day2_pred_upper': types.Integer(),
            'day3_pred_upper': types.Integer(),
            'day4_pred_upper': types.Integer(),
            'day5_pred_upper': types.Integer(),
            'day6_pred_upper': types.Integer(),
            'day7_pred_upper': types.Integer(),
            'day1_pred_lower': types.Integer(),
            'day2_pred_lower': types.Integer(),
            'day3_pred_lower': types.Integer(),
            'day4_pred_lower': types.Integer(),
            'day5_pred_lower': types.Integer(),
            'day6_pred_lower': types.Integer(),
            'day7_pred_lower': types.Integer(),
            'day1_date': types.Date(),
            'day2_date': types.Date(),
            'day3_date': types.Date(),
            'day4_date': types.Date(),
            'day5_date': types.Date(),
            'day6_date': types.Date(),
            'day7_date': types.Date(),
            'model': types.String(),
            'dt': types.Date()
            }
    
    engine = create_engine(connection_str)
    
    # open up the connection to the database, and insert the values in test_df
    print(f"Attempting to add predictions to database.....")
    try:
        with engine.connect() as connection:
            df.to_sql(table_name, con=connection, dtype=dtypes, index=False, if_exists='append', method='multi')
        print(f"Succeeded")
    except Exception as e:
        print(f"Failed because: {e}")
        
def create_connection_string(info_dict: dict) -> str:
    return f"{info_dict['driver']}://{info_dict['username']}:{info_dict['password']}@{info_dict['host']}:{info_dict['port']}/{info_dict['database']}"
        