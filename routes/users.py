from utils import common, tables
from utils.common import app, session

from utils import users

from flask import request

from sqlalchemy import select

import multiprocessing
from datetime import datetime, timezone

#CRUD: Create, Read, Update, Delete

user_lock=multiprocessing.Lock() #We lock not because of the IDs (autoincrement is enough), but because of the usernames

@app.route("/users/create")
def create():
    result={}
    

    with user_lock:
        user=tables.User()
        username=request.json["username"]
        if username is not None:
            if users.checkIfUsernameExists(username):
                result["error"]="USERNAME_EXISTS"
                return result
        
        user.password_salt=common.generate_salt()

        users.assign_json_to_user(user, request.json)
        user.creation_time=datetime.now(timezone.utc)
        session.add(user)
        session.commit()
        return result

@app.route("/users/info")
@common.authenticate
def info():
    result={}
    
    uid=request.json["uid"]
    id=request.json.get("id",uid) #By default, use the current uid if another id wasn't specified

    user=session.get(tables.User, id)
    if user is None:
        result["error"]="NOT_FOUND"
        return result
    for col in user.__mapper__.attrs.keys():
        if col in ["id", "creation_time"]:
            continue 
        value=getattr(user,col)
        result[col]=value
    
    result["creation_time"]=common.convert_from_datetime(value, common.UTC)
    return result
        
@app.route("/users/edit")
@common.authenticate
def modify():
    #Technically, we lock for longer than we need to (we only need to lock when changing usernames, not for assigning the rest of the info). However, the benefits of accidentally causing a deadlock is outweigh the slight delays caused by overeager locking.
    result={}
    
    uid=request.json["uid"]

    with user_lock:
        user=session.get(tables.User, uid)
        
        username=request.json.get("username", user.username)
        
        if user.username==username:
            result["error"]="NAME_NOT_CHANGED"
            return result
        else:
             if users.checkIfUsernameExists(username):
                result["error"]="NAME_ALREADY_TAKEN"
                return result
                
             users.assign_json_to_user(user, request.json)
             session.commit()
             return result

@app.route("/users/delete")
@common.authenticate
def delete():
    result={}
    uid=request.json["uid"]
    id=request.json.get("id",uid)
    
    user=session.get(tables.User,id)
    deleted_user=session.get(tables.User, request.json["id"])
    
    if deleted_user.id!=user.id: #Add check later for root user
        result["error"]="INSUFFICIENT_PERMISSION"
        return result
    
    with user_lock:
        session.delete(deleted_user)
        session.commit()

    return result

@app.route("/users/signin")
def signin():
    username=request.json["username"]
    password=request.json["password"]
    
    if username=="root": #Hardcoded in
        uid=-1
    else:
        with user_lock:
            user=session.scalars(select(tables.User).where(tables.User.username==username)).first()
        if user is None:
            return {"error": "USER_NOT_FOUND"}
        uid=user.id

    return common.authentication_wrapper(uid, password, lambda: {"uid": uid})
