#in search, allow for all job applications to show up.

from utils import common, tables
from utils.common import app
from utils import bookings
from flask import request
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import random

@app.route("/bookings/create")
@common.authenticate
def create_booking():
    result={}
    
    uid=request.json["uid"]
    with Session(common.database) as session:
        booking=tables.Booking()
        session.add(booking)
        
        booking.author=uid
        ret=bookings.assign_json_to_booking(session, booking, request.json, True)
        
        if ret==-1:
            session.remove(booking)
            result["error"]="BLOCKED"
        
        bookings.code=random.randint(10000,10000000)
        session.commit()
    
    return result

@app.route("/bookings/info")
@common.authenticate
def booking_info():
    result={}
    
    uid=request.json["uid"]
    with Session(common.database) as session:
        booking=bookings.getBooking(request.json["id"],session=session)
        
        if uid not in [booking.author, booking.buisness]:
            result["error"]="INSUFFICIENT_PERMISSION"
            return result
        
        timezone=ZoneInfo(request.json.get("timezone","UTC"))
        
        for col in booking.__mapper__.attrs.keys():
            value=getattr(booking,col)
            if col=="id":
                continue
            elif col.endswith("_datetime"):
                value=value.localize(timezone).strftime(common.DATETIME_FORMAT)
            if col=="services":
                value=common.fromStringList(value)
                
            result[col]=value
    return result

@app.route("/bookings/edit")
@common.authenticate
def booking_edit():  
    result={}
    
    with Session(common.database) as session:
        booking=bookings.getBooking(request.json["id"],session=session)
        
        if booking is None:
            result["error"]="DOES_NOT_EXIST"
            return result
        elif request.json["uid"]!=booking.author:
             result["error"]="INSUFFICIENT_PERMISSION"
             return result
        
        ret=bookings.assign_json_to_booking(session, booking, request.json, False)
        
        if ret==-1:
            result["error"]="BLOCKED"
            return result
        else:
            session.commit()
            return result

@app.route("/bookings/cancel")
@common.authenticate
def booking_cancel():
    result = {}
    
    uid=request.json["uid"]
    
    with Session(common.database) as session:
        booking=bookings.getBooking(request.json["id"],session=session)
        
        if booking is None:
            result["error"]="DOES_NOT_EXIST"
            return result
        elif uid not in [booking.author, booking.buisness]:
             result["error"]="INSUFFICIENT_PERMISSION"
             return result
        
        now=datetime.datetime.now(timezone.utc)
        
        if not(uid==booking.author and booking.start_datetime < now): #Individuals can only cancel before the start time
            result["error"]="TOO_LATE"
            return result
        elif not(uid==booking.buisness and booking.start_datetime >= now): #Buisnesses can only cancel after the appointment's start time (in case of no-shows)
            result["error"]="TOO_EARLY"
            return result
        session.delete(booking)
        session.commit()
    return result

@app.route("/bookings/list")
@common.authenticate
def booking_list():
    result = {}
    
    uid=request.json["uid"]
    with Session(common.database) as session:
        query=select(tables.Booking.id).where(tables.Booking.id==uid | tables.Booking.buisness==uid)
        
        result["bookings"]=list(session.scalars(query).all())
        return result

@app.route("/bookings/checkout") #When the appointment is over (the code is still used by the customer to authenticate themselves to the buisness when they first walk-in
@common.authenticate
def booking_checkout():
    result = {}
    uid=request.json["id"]
    
    with Session(common.database) as session:
        booking=bookings.getBooking(request.json["id"],session=session)
        
        if booking is None:
            result["error"]="DOES_NOT_EXIST"
            return result
        elif uid !=booking.buisness:
             result["error"]="INSUFFICIENT_PERMISSION"
             return result
        
        checkout_message=tables.Message()
        checkout_message.recipient=booking.author
        checkout_message.time_posted=datetime.now(common.UTC)
        checkout_message.title="Your appointment is over"
        checkout_message.text=f"The buisness{booking.buisness} has marked your booking {booking.id} as over. Thank you for using us!"
        
        session.delete(booking)
        session.add(checkout_message)
        
        session.commit()
        
        return result