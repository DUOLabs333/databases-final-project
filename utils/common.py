#Should be imported by all relevant files

import sys,os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, request
from flask_cors import CORS
from zoneinfo import ZoneInfo

database = create_engine("sqlite:///test_db.db")
session=scoped_session(sessionmaker(bind=database))
app=Flask("backend_server")

@app.teardown_appcontext
def remove_session(exception=None):
    session.remove()

from utils import tables

def post_wrap(func):
    def wrapper(*args,**kwargs):
        key="methods"
        kwargs[key]=kwargs.get(key,[])
        if key in kwargs:
            if "POST" not in kwargs[key]:
                kwargs[key].append("POST")
        return func(*args,**kwargs)
    return wrapper

setattr(app,"route",post_wrap(app.route))
            
CORS(app)

import functools, hashlib, random, string

UTC=ZoneInfo("UTC")
DATETIME_FORMAT="%Y-%m-%d %H:%M:%S.%f"

def pass_hash(password, salt):
    return hashlib.sha256((password+salt).encode("utf-8")).hexdigest()

def generate_salt():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def authentication_wrapper(uid, password, func): 
   has_access=False
   if uid==-1 and password=="root": #Hardcoded in, so we can bootstrap populating the table (and avoid a catch-22)
       has_access=True
   else:
       user=session.get(tables.User,uid)
       if user is None:
           return {"error": "USER_NOT_FOUND"}

       has_access=(user.password_hash==pass_hash(password,user.password_salt))
   
   if not has_access:
       return {"error":"PASSWORD_INCORRECT"}
   else:
       return func()

def authenticate(func):
   @functools.wraps(func)
   def wrapper(*args,**kwargs):
       return authentication_wrapper(request.json["uid"], request.json["password"], lambda : func(*args, **kwargs))
   return wrapper

def last(lst):
    if len(lst)==0:
        return None
    else:
        return lst[-1]
