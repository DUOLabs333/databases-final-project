#Should be imported by all relevant files

# scoped sessions rather than creating a new db session each time operation needs to be performed
import sys,os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from flask import Flask, request
from flask_cors import CORS
from zoneinfo import ZoneInfo

database = create_engine("sqlite:///test_db.db")
Session = scoped_session(sessionmaker(bind=database))

import utils.users as users

@app.teardown_appcontext
def remove_session(exception=None):
    Session.remove()

app=Flask("backend_server")

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

import functools

UTC=ZoneInfo("UTC")
DATETIME_FORMAT="%Y-%m-%d %H:%M:%S.%f"
 
def authenticate(func):
   @functools.wraps(func)
   def wrapper(*args,**kwargs):
       uid=request.json["uid"]
       hash=request.json["key"]
       
       user=users.getUser(uid)
       
       has_access=(user is not None) and (hash==user.password_hash)
       
       if not has_access:
           result={"error":"ACCESS_DENIED"}
           return result
       else:
           return func(*args,**kwargs)
   return wrapper

def last(lst):
    if len(lst)==0:
        return None
    else:
        return lst[-1]
