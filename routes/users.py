from utils import common, tables
from utils.common import app

from utils import users

from flask import request

from sqlalchemy import select
from sqlalchemy.orm import Session

import multiprocessing
from datetime import datetime, timezone

#CRUD: Create, Read, Update, Delete

user_lock=multiprocessing.Lock() #We lock not because of the IDs (autoincrement is enough), but because of the usernames

@app.route("/users/create")
def create():
    result={}
    
    user_lock.acquire()
    
    with Session(common.database) as session:
        user=tables.User()
        
        username=request.json["username"]
        if username is not None:
            if users.checkIfUsernameExists(username):
                user_lock.release()
                result["error"]="USERNAME_EXISTS"
                return result
                
        users.assign_json_to_user(user, request.json)
        
        user.creation_time=datetime.now(timezone.utc)
        session.add(user)
        session.commit()
        user_lock.release()
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
            result["error"]="NOT_FOUND"
            return result
        for col in user.__mapper__.attrs.keys():
            if col in ["id", "creation_time"]:
                continue 
            value=getattr(user,col)
            result[col]=value
        
        result["creation_time"]=user.creation_time.strftime(common.DATETIME_FORMAT)
        return result
        
@app.route("/users/edit")
@common.authenticate
def modify():
    result={}
    
    uid=request.json["uid"]
    with Session(common.database) as session:
        user=users.getUser(uid,session)
        
        username=request.json.get("username", user.username)
        
        if user.username==username:
            user_lock.release()
            result["error"]="NAME_NOT_CHANGED"
            return result
        else:
             user_lock.acquire()
             if users.checkIfUsernameExists(username):
                user_lock.release()
                result["error"]="NAME_ALREADY_TAKEN"
                return result
                
             users.assign_json_to_user(user, request.json)
             user_lock.release()
             session.commit()
             return result

@app.route("/users/delete")
@common.authenticate
def delete():
    result={}
    with Session(common.database) as session:        
        uid=request.json["uid"]
        id=request.json.get("id",uid)
        user=users.getUser(id,session)
        
        deleted_user=users.getUser(request.json["id"])
        
        if deleted_user.id!=user.id: #Add check later for root user
            result["error"]="INSUFFICIENT_PERMISSION"
            return result
         
        user_lock.acquire()  
        session.delete(deleted_user)
        session.commit()
        user_lock.release()
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