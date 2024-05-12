from utils import common, tables

from utils.common import app, session

from utils import availabilities

from flask import request, send_file, current_app
from sqlalchemy import select
import pgeocode

import os
from pathlib import Path
from zoneinfo import ZoneInfo
import math

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
            value=common.convert_from_datetime(value, timezone)
            
        elif col.endswith("_time"):
            value=common.convert_from_datetime(value, timezone, time=True)

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

dist = pgeocode.GeoDistance('US') #We will have to find a way to support other countries dynamically (probably need another field in user for country)

@app.route("/availabilities/search")
def availability_search():
    
    result={}
    
    timezone=ZoneInfo(request.json.get("timezone","UTC"))
    
    start_datetime=common.convert_to_datetime(request.json["start_datetime"], timezone)

    end_datetime=common.convert_to_datetime(request.json["end_datetime"], timezone)    
    services=request.json["services"]
    
    zip_code=request.json.get("zip_code", None)
    
    start=request.json.get("start",0)
    
    length=request.json.get("length", 50)
    
    query=select(tables.Availability_to_Service.id, tables.Availability.business, tables.User.zip_code, tables.Service.price).join_from(tables.Availability, tables.Availability_to_Service, tables.Availability.id==tables.Availability_to_Service.availability).join(tables.User, tables.Availability.business==tables.User.id).join(tables.Service, tables.Availability_to_Service.service==tables.Service.id).where(availabilities.get_availabilities_in_range(start_datetime, end_datetime, services) & tables.Availability.services_clause(services)).order_by(tables.Service.price.asc()) #The ORDER BY SERVICES.PRICE ASC clause ensures that instances of the same service from the same business are listed in order of increasing price. Therefore, when iterating through the result set of the query, we can simply select the first instance of the service from each business that we encounter, as it will guarantee that we will always retrieve the cheapest offering for each business.


    rows=[]
    unique_businesses=set()
     
    for row in session.execute(query).all():
        if availabilities.check_for_conflict(start_datetime, end_datetime, row[1]):
            continue #Obviously, if this would create a conflict with a business, you can not use it
        
        distance=0
        
        row_keys=["availability_to_service", "business", "distance", "price"]
        rows.append({row_keys[i]: row[i] for i in range(len(row))})
        business=rows[-1]["business"]

        if business in unique_businesses:
            rows.pop()
            continue
        else:
            unique_businesses.add(business)
        
        if zip_code:
            distance=dist.query_postal_code(zip_code, row[1])
            if math.isnan(distance):
                distance=float("inf") #So it will be the last 

        rows[-1]["distance"]=distance
    
    if zip_code is not None:
        rows.sort(reverse=True, key= lambda row: row["distance"])
    
    end=min(start+length+1, len(rows)) #The index of the last element that will be returned

    result["info"]=rows[start: end]
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
