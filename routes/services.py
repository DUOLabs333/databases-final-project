from utils import common, tables

from utils.common import app

from utils import services

from flask import request
from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session
import pgeocode

import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

NUM_TO_DAY=availabilities.DAY_TO_NUM.keys()


@app.route("/services/create")
@common.authenticate
def create_service():
    result={}
    
    uid=request.json["uid"]
    
    with Session(common.database) as session:
        service=tables.Service()
        session.add(service)
        
        session.commit() #So we can get an id
        
        service.buisness=uid
        services.assign_json(service, request.json)
                    
        session.commit()

    return result

@app.route("/services/info")
def availability_info():
    result={}
    
    with Session(common.database) as session:
        service=session.get(tables.Service, request.json["id"])
        
        if service is None:
            result["error"]="NOT_FOUND"
            return result
        
        for col in availability.__mapper__.attrs.keys():
            value=getattr(service,col)
            if col=="id":
                continue                
            result[col]=value
    return result

@app.route("/services/edit")
@common.authenticate
def availability_edit(): #Have to reassign all availbility that is attached to service     
    return availabilities.availability_change(request, "edit") #Change to services.modify, with the same arguments
    
@app.route("/services/delete")
@common.authenticate
def availability_delete():     
    return availabilities.availability_change(request, "delete")
