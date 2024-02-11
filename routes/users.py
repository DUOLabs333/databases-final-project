from utils import common, tables, balance
from utils.common import app, appendToStringList, removeFromStringList

from utils import users, posts

from flask import request

from sqlalchemy import select, desc, not_
from sqlalchemy.orm import Session
import multiprocessing
import random, string,time, heapq, json
from datetime import datetime
from zoneinfo import ZoneInfo

lock=multiprocessing.Lock() #We lock not because of the IDs (autoincrement is enough), but because of the usernames

#Lock table when deleting, creating, and renaming

def checkIfUsernameExists(username): #You must have the USERS database locked, and you must not unlock it until you placed the (new) username into the database
    with Session(common.database) as session:
        return session.scalars(select(tables.User.id).where(tables.User.username==username)).first() is not None

#CRUD: Create, Read, Update, Delete

@app.route("/users/create")
def create():
    result={}
    
    data=request.json
    lock.acquire()
    
    username=data["username"]
    
    if checkIfUsernameExists(username):
        lock.release()
        result["error"]="USERNAME_EXISTS"
        return result
        
    user=tables.User()
    
    for attr in ["username","password_hash"]:
        setattr(user,attr,data[attr])
        
    for attr in ["location_long", "location_lat"]:
        if attr in data:
            setattr(user,attr, data[attr])
    
    user.creation_time=datetime.now(tz=ZoneInfo("UTC"))
    
    with Session(common.database) as session:
        
        session.add(user)
        session.commit()
        
        lock.release()
        result["id"]=user.id
    return result

@app.route("/users/info")
@common.authenticate
def info():
    result={}
    
    uid=request.json["uid"]
    id=request.json.get("id",uid) #By default, use the current uid
    
    with Session(common.database) as session:
        user=users.getUser(id,session)
        if user is None:
            result["error"]="USER_NOT_FOUND"
            return result
        for col in user.__mapper__.attrs.keys():
            if col in ["id", "password_hash"]:
                continue 
            value=getattr(user,col)
            result[col]=value
        
        return result
        
@app.route("/users/edit")
@common.authenticate
def modify():
    result={}
    username=request.json.get("username",None)
    password=request.json.get("password_hash",None)
    uid=request.json["uid"]
    with Session(common.database) as session:
        user=users.getUser(uid,session)
        
        for col in user.__mapper__.attrs.keys():
            if col not in request.json:
                continue
            if col=="username":
                if getattr(user,col)==request.json[col]:
                    result["error"]="NAME_NOT_CHANGED"
                    return json
                else:
                    lock.acquire()
                    if checkIfUsernameExists(request.json[col]):
                        result["error"]="NAME_ALREADY_TAKEN"
                        lock.release()
                        return result
                    else:
                        setattr(user,col,request.json[col])
                        lock.release()
            else:
                setattr(user,col, request.json[col])
        session.commit()
        return result

@app.route("/users/delete")
@common.authenticate
def delete():
    result={}
    with Session(common.database) as session:
        lock.acquire()
        
        uid=request.json["uid"]
        id=request.json.get("id",uid)
        user=users.getUser(id,session)
        
        deleted_user=users.getUser(request.json["id"])
        
        if deleted_user.id!=user.id: #Add check later for root user
            result["error"]="INSUFFICIENT_PERMISSION"
            return result
            
        session.delete(deleted_user)
        session.commit()
        lock.release()
        return result

@app.route("/users/signin")
def signin():
    result={}
    with Session(common.database) as session:
        username=request.json["username"]
        password=request.json["password_hash"]
            
        user=session.scalars(select(tables.User).where(tables.User.username==username)).first()
        
        if user is None:
            result["error"]="USER_NOT_FOUND"
            return result
        
        if password!=user.password_hash:
            result["error"]="PASSWORD_INCORRECT"
            return result
            
        result["uid"]=user.id
        return result                        