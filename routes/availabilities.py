from utils import common, tables

from utils.common import app, session

from utils import availabilities

from flask import request, send_file, current_app
from sqlalchemy import select, tuple_
import pgeocode

import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

NUM_TO_DAY=availabilities.DAY_TO_NUM.keys()


@app.route("/availabilities/create")
@common.authenticate
def create_post():
    result={}
    
    uid=request.json["uid"]
    
    availability=tables.Availability()
    session.add(availability)

    session.commit() #So we can get an id
    
    availability.business=uid
    availabilities.assign_json_to_availability(availability, request.json)
                
    session.commit()

    if availability.available==False: #A block
        availabilities.reassign_or_cancel_bookings(availability)
        
    return result

@app.route("/availabilities/info")
def availability_info():
    result={}
    
    availability=session.get(tables.Availability, request.json["id"])
    
    if availability is None:
        result["error"]="NOT_FOUND"
        return result
    
    timezone=ZoneInfo(request.json.get("timezone","UTC"))
    
    for col in availability.__mapper__.attrs.keys():
        value=getattr(availability,col)
        if col=="id":
            continue
        elif col.endswith("_datetime"):
            value=value.astimezone(timezone).strftime(common.DATETIME_FORMAT)
        elif col.endswith("_time"):
            value=value.astimezone(timezone).isoformat()
        elif col=="days_supported":
            value=[NUM_TO_DAY[i] for i in range(len(NUM_TO_DAY)) if value & (1 << i) != 0 ]
        if col=="services":
            query=select(tables.Availability_to_Service.service).where(tables.Availability_to_Service.availability==availability.id)
            value=session.scalars(query).all()
            
        result[col]=value
    return result

@app.route("/availabilities/edit")
@common.authenticate
def availability_edit():     
    return availabilities.availability_change(request, "edit")
    
@app.route("/availabilities/delete")
@common.authenticate
def availability_delete():     
    return availabilities.availability_change(request, "delete")

dist = pgeocode.GeoDistance('US')

@app.route("/availabilities/search")
def availability_search():
    
    result={}
    
    timezone=ZoneInfo(request.json.get("timezone","UTC"))
    
    start_datetime=datetime.strptime(request.json["start_datetime"], common.DATETIME_FORMAT).replace(tzinfo=timezone).astimezone(common.UTC)
    
    end_datetime=datetime.strptime(request.json["end_datetime"], common.DATETIME_FORMAT).replace(tzinfo=timezone).astimezone(common.UTC)
    
    services=request.json["services"]
    
    zip_code=request.json.get("zip_code", None)
    
    start=request.json.get("start",0)
    
    length=request.json.get("length", 50)
    
    query=select(tables.Availability.business, tables.User.zip_code).distinct().join(tables.User, tables.Availability.business==tables.User.id).where(availabilities.get_availabilities_in_range(start_datetime, end_datetime, services))
    
    rows=[]
     
    for row in session.execute(query).all():
        if availabilities.check_for_conflict(session, start_datetime, end_datetime, row[0]):
            result["error"]="CONFLICT"
            return result
            
        if zip_code is None:
            rows.append((row[0], 0)) #Assume that the distance is 0
        else:
            rows.append((row[0], dist.query_postal_code(zip_code, row[1])))
    
    if zip_code is not None:
        rows.sort(reverse=True, key= lambda row: row[1])
    
    end=min(start+length+1, len(rows)) #The index of the last element that will be returned 
    rows=rows[start: end]
    
    businesses, distances = list(zip(*rows)) or ((), ()) #Short-circuit in case of empty rows
    
    result["businesses"]=list(businesses)
    result["distances"]=list(distances)
    result["end"]=end
    
    return result

@app.route("/upload")
@common.authenticate
def image_upload():
    result={}
    
    media_folder = os.path.join(current_app.root_path,"static","media")
    Path(media_folder).mkdir(parents=True,exist_ok=True)
    
    media = request.files.get['media']
    type=media.content_type
    size=media.content_length
    
    if size>10*(10**6):
        result["error"]="FILE_TOO_LARGE"
        return result

    upload=tables.Upload()
            
    upload.type=type
    
    session.add(upload)
    session.commit()
    
    media.save(os.path.join(media_folder, str(upload.id)))
        
    result["id"]=upload.id
    return result
    
@app.route("/media")
def image():
    
    id=request.json["id"]
    
    media_folder = os.path.join(current_app.root_path,"static","media")
    
    type=session.scalars(select(tables.Upload.type).where(tables.Upload.id==id).limit(1)).first()
        
    return send_file(os.path.join(media_folder, str(id)), mimetype=type)
