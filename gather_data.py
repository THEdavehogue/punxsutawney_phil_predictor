import os
import json
import numpy as np
import pandas as pd
import requests
from time import sleep
from datetime import datetime, time, timedelta
from progressbar import ProgressBar
from pymongo import MongoClient

KEY = os.environ['DARK_SKY_KEY']
LAT = '40.9310'
LON = '-78.9572'
EARLY_SPRING_YEARS = ['1950', '1970', '1975', '1983', '1986', '1988', '1990',
                      '1995', '1997', '1999', '2007', '2011', '2013', '2016']


def API_call(url):
    '''
    Make API call for the given url

    INPUT:
        url: str, url for API call

    OUTPUT:
        response: HTTP response object
    '''

    try:
        response = requests.get(url)
    except:
        sleep(5)
        response = API_call(url)
    return response


def scrape_weather_data(year, db_coll):
    '''
    Get Punxsutawney weather data for a given Groundhog Day

    INPUT:
        year: str, year of weather data
        db_coll: pymongo collection for storing weather data
    '''

    time = '{}-02-02T12:00:00Z'.format(year) # Noon UTC = 7am Punxsutawney
    url = 'https://api.darksky.net/forecast/{}/{},{},{}'.format(KEY, LAT, LON, time)

    response = API_call(url)

    if response.status_code == 200:
        forecast = response.json()
        if year in EARLY_SPRING_YEARS:
            forecast[u'prediction'] = 1
        else:
            forecast[u'prediction'] = 0
        db_coll.insert_one(forecast)
    else:
        scrape_weather_data(year, db_coll)


def populate_weather_db(db_coll):

    years = map(str, np.arange(1944, 2018))

    print 'Checking weather table . . .'
    if pred_coll.count() < len(years):
        print 'Refreshing weather observations . . .'
        pred_coll.drop()
        pbar = ProgressBar()
        for year in pbar(years):
            scrape_weather_data(year, pred_coll)
    else:
        print 'Weather table already populated!'


def unix_to_datetime(unix_time):
    '''
    Convert UNIX time to datetime

    INPUT:
        unix_time: int, UNIX time (seconds since 1970-01-01 00:00:00)

    OUTPUT:
        new_dt: datetime object, datetime representation of unix_time
    '''

    orig = datetime(1970, 1, 1, 0, 0, 0, 0)
    new_dt = orig + timedelta(seconds=unix_time)
    return new_dt


def empty_df(hourly=False):
    '''
    Function to create an empty pandas DataFrame object (used in mongo_to_pandas)

    INPUT: None

    OUTPUT: empty pandas DataFrame object
    '''
    if not hourly:
        df = pd.DataFrame(columns=['date',
                                   'max_temp',
                                   'min_temp',
                                   'dew_point',
                                   'humidity',
                                   'condition',
                                   'moon_phase',
                                   'precip_type',
                                   'visibility',
                                   'wind_bearing',
                                   'wind_speed',
                                   'prediction'])
    else:
        df = pd.DataFrame(columns=['date',
                                   'time',
                                   'feels_like_temp',
                                   'dew_point',
                                   'humidity',
                                   'precip_type',
                                   'summary',
                                   'actual_temp',
                                   'visibility',
                                   'wind_bearing',
                                   'wind_speed'])
    return df



def parse_record_daily(rec):
    '''
    Function to parse Mongo record into a pandas Series object

    INPUT:
        rec: record from MongoDB

    OUTPUT:
        row: Mongo record converted to pandas Series
    '''

    daily = rec['daily']['data'][0]
    date = unix_to_datetime(daily['time']).date()
    if daily.get('icon', None) == 'partly-cloudy-day' or \
       daily.get('icon', None) == 'partly-cloudy-night':
        condition = 'partly-cloudy'
    else:
        condition = daily.get('icon', None)

    row = {'date': date,
           'max_temp': daily.get('temperatureMax', None),
           'min_temp': daily.get('temperatureMin', None),
           'dew_point': daily.get('dewPoint', None),
           'humidity': daily.get('humidity', None),
           'condition': condition,
           'moon_phase': daily.get('moonPhase', None),
           'precip_type': daily.get('precipType', 'None'),
           'visibility': daily.get('visibility', None),
           'wind_bearing': daily.get('windBearing', None),
           'wind_speed': daily.get('windSpeed', None),
           'prediction': rec.get('prediction', None)}
    return pd.Series(row)


def parse_record_hourly(rec):
    '''
    Function to parse Mongo record into a pandas Series object

    INPUT:
        rec: record from MongoDB

    OUTPUT:
        row: Mongo record converted to pandas DataFrame
    '''
    rows = empty_df(hourly=True)
    offset = rec['offset']
    hourly = rec['hourly']['data']
    date = unix_to_datetime(rec['daily']['data'][0]['time']).date()
    for hour in hourly:
        local_time = unix_to_datetime(hour['time']) + timedelta(hours=offset)
        row = {'date': date,
               'time': local_time.time(),
               'feels_like_temp': hour.get('apparentTemperature'),
               'dew_point': hour.get('dewPoint'),
               'humidity': hour.get('humidity'),
               'precip_type': hour.get('precipType'),
               'summary': hour.get('summary'),
               'actual_temp': hour.get('temperature'),
               'visibility': hour.get('visibility'),
               'wind_bearing': hour.get('windBearing', 0),
               'wind_speed': hour.get('windSpeed', 0),
               'prediction': rec.get('prediction')}
        rows = rows.append(pd.Series(row), ignore_index=True)
    return rows



def mongo_to_pandas(db_coll):
    '''
    Convert JSON records in MongoDB collection to pandas DataFrame

    INPUT:
        db_coll: pymongo collection

    OUTPUT:
        df: Pandas DataFrame
    '''

    c = db_coll.find()
    records = list(c)
    df_daily = empty_df(hourly=False)
    df_hourly = empty_df(hourly=True)
    pbar = ProgressBar()
    for rec in pbar(records):
        day = parse_record_daily(rec)
        df_daily = df_daily.append(day, ignore_index=True)
        hours = parse_record_hourly(rec)
        df_hourly = df_hourly.append(hours, ignore_index=True)
    for df in [df_daily, df_hourly]:
        df['wind_bearing'] = df['wind_bearing'].astype(int)
        df['prediction'] = df['prediction'].astype(int)
    df_hourly['precip_type'] = df_hourly['precip_type'].fillna('None')
    return df_daily, df_hourly


def scrub_data(df, hourly=False):
    if not hourly:
        df_daily = df
        df_precip_dummies = pd.get_dummies(df['precip_type'], drop_first=True)
        df_condition_dummies = pd.get_dummies(df['condition'], drop_first=True)
        df_daily = df.drop(['date', 'condition', 'precip_type'], axis=1)
        df_daily = pd.concat([df_daily, df_precip_dummies, df_condition_dummies], axis=1)
        return df_daily
    else:
        df_hourly = df
        mask_a = df_hourly['time'] >= time(7, 0)
        mask_b = df_hourly['time'] <= time(9, 0)
        df_morning = df_hourly[mask_a & mask_b]
        dates = df_morning['date'].unique()
        df_summaries = pd.DataFrame(columns = df_morning.columns)

        for dt in dates:
            new_row = {}
            df_slice = df_morning[df_morning['date'] == dt]
            new_row['actual_temp'] = df_slice['actual_temp'].mean()
            new_row['date'] = dt
            new_row['dew_point'] = df_slice['dew_point'].mean()
            new_row['feels_like_temp'] = df_slice['feels_like_temp'].mean()
            new_row['humidity'] = df_slice['humidity'].mean()
            try:
                new_row['precip_type'] = df_slice['precip_type'].mode()[0]
            except:
                new_row['precip_type'] = 'None'
            new_row['prediction'] = df_slice['prediction'].mean()
            try:
                new_row['summary'] = df_slice['summary'].mode()[0]
            except:
                new_row['summary'] = 'Overcast'
            new_row['time'] = 'morning avg'
            new_row['visibility'] = df_slice['visibility'].mean()
            new_row['wind_bearing'] = df_slice['wind_bearing'].mean()
            new_row['wind_speed'] = df_slice['wind_speed'].mean()
            df_summaries = df_summaries.append(pd.Series(new_row), ignore_index=True)
        df_precip_dummies = pd.get_dummies(df_summaries['precip_type'], drop_first=True)
        df_summary_dummies = pd.get_dummies(df_summaries['summary'], drop_first=True)
        df_summaries = df_summaries.drop(['date', 'precip_type', 'summary', 'time'], axis=1)
        df_summaries = pd.concat([df_summaries, df_precip_dummies, df_summary_dummies], axis=1)
        return df_summaries

if __name__ == '__main__':

    db_client = MongoClient()
    db = db_client['groundhog_day']
    pred_coll = db['predictions']

    populate_weather_db(pred_coll)

    df_daily, df_hourly = mongo_to_pandas(pred_coll)
    df_daily_scrubbed = scrub_data(df_daily, hourly=False)
    df_hourly_scrubbed = scrub_data(df_hourly, hourly=True)
    df_daily.to_pickle('data/groundhog_daily.pkl')
    df_hourly.to_pickle('data/groundhog_hourly.pkl')
    df_daily_scrubbed.to_pickle('data/groundhog_daily_scrubbed.pkl')
    df_hourly_scrubbed.to_pickle('data/groundhog_hourly_scrubbed.pkl')
