import os
import json
import numpy as np
import pandas as pd
import requests
from time import sleep
from datetime import datetime, timedelta
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


def empty_df():
    '''
    Function to create an empty pandas DataFrame object (used in mongo_to_pandas)

    INPUT: None

    OUTPUT: empty pandas DataFrame object
    '''
    df = pd.DataFrame(columns=['year',
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
    return df


def parse_record(rec):
    '''
    Function to parse Mongo record into a pandas Series object

    INPUT:
        rec: record from MongoDB

    OUTPUT:
        row: Mongo record converted to pandas Series
    '''

    daily = rec['daily']['data'][0]
    year = unix_to_datetime(daily['time']).year
    if daily.get('icon', None) == 'partly-cloudy-day' or \
       daily.get('icon', None) == 'partly-cloudy-night':
        condition = 'partly-cloudy'
    else:
        condition = daily.get('icon', None)

    row = {'year': year,
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
    df = empty_df()
    pbar = ProgressBar()
    for rec in pbar(records):
        row = parse_record(rec)
        df = df.append(row, ignore_index=True)
        df['year'] = df['year'].astype(int)
        df['wind_bearing'] = df['wind_bearing'].astype(int)
        df['prediction'] = df['prediction'].astype(int)
    return df


if __name__ == '__main__':

    db_client = MongoClient()
    db = db_client['groundhog_day']
    pred_coll = db['predictions']

    populate_weather_db(pred_coll)

    df = mongo_to_pandas(pred_coll)
    df.to_csv('data/groundhog.csv')
