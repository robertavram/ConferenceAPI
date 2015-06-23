
import json
import os
import time
import uuid
import re

from google.appengine.api import urlfetch

from datetime import datetime
import datetime as datetimeTypes


def is_valid_name(name):
    ''' Checks if a name is valid '''
    if not name or name != name.title() or len(name) < 3 or len(name) > 50:
        return False
    regex = re.compile(r"^[^\W0-9_]+([ \-'][^\W0-9_]+)*?$", re.U)
    return regex.match(name) is not None


def getUserId(user, id_type="email"):
    if id_type == "email":
        return user.email()

    if id_type == "oauth":
        """A workaround implementation for getting userid."""
        auth = os.getenv('HTTP_AUTHORIZATION')
        bearer, token = auth.split()
        token_type = 'id_token'
        if 'OAUTH_USER_ID' in os.environ:
            token_type = 'access_token'
        url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?%s=%s'
               % (token_type, token))
        user = {}
        wait = 1
        for i in range(3):
            resp = urlfetch.fetch(url)
            if resp.status_code == 200:
                user = json.loads(resp.content)
                break
            elif resp.status_code == 400 and 'invalid_token' in resp.content:
                url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?%s=%s'
                       % ('access_token', token))
            else:
                time.sleep(wait)
                wait = wait + i
        return user.get('user_id', '')


def make_date(date_string):
    ''' Returns a datetime.date from a datestring '''
    return datetime.strptime(date_string[:10], "%Y-%m-%d").date()


def make_time(time_string):
    ''' Returns a datetime.time from a timestring '''
    return datetime.strptime(time_string[:5], "%H:%M").time()


def combine_date(my_date, my_time):
    ''' Combines a datetime.date with a datetime.time into a datetime.datetime object '''
    return datetime.combine(my_date, my_time)


def time_to_minutes(my_time):
    ''' takes either a string or unicode of the form HH:MM or a datetime.time
    and returns the total minutes (int)'''
    if isinstance(my_time, str) or isinstance(my_time, unicode):
        t = my_time.split(":")
        return (int(t[0]) * 60) + int(t[1])
    elif isinstance(my_time, datetimeTypes.time):
        return (my_time.hour * 60) + my_time.minute
    else:
        raise TypeError("time needs to be string or datetime.time")


def minutes_to_timestring(mymin):
    ''' takes an int minutes and returns a timestring HH:MM '''
    minutes = mymin % 60
    hours = mymin / 60
    minutes = str(minutes) if minutes > 9 else '0' + str(minutes)
    hours = str(hours) if hours > 9 else '0' + str(hours)
    return str(hours) + ":" + minutes


def clean_s(mys):
    ''' remove special characters from string '''
    pattern = re.compile("[^\w']")
    return pattern.sub(' ', mys)
