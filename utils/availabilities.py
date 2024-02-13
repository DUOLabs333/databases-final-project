import utils.common as common
import utils.tables as tables
from sqlalchemy import or_, true, select
from sqlalchemy.orm import Session
from datetime import datetime, time
from zoneinfo import ZoneInfo

DAY_TO_NUM={"MONDAY":0, "TUESDAY":1, "WEDNESDAY":2, "THURSDAY":3, "FRIDAY":4, "SATURDAY":5, "SUNDAY":6}

def getAvailability(availability_id,session=None):
    return common.getItem(tables.Availability,availability_id,session)

def assign_json_to_availability(availability, data):
    timezone=ZoneInfo(data.get("timezone","UTC"))
    for col in availability.__mapper__.attrs.keys():
        if col in data:
            value=data[col]
        else:
            continue
        
        if col in ["id","author"]:
            continue
        if col.endswith("_datetime"):
            value=datetime.strptime(value, common.DATETIME_FORMAT).replace(tzinfo=timezone).localize(common.UTC)
        elif col.endswith("_time"):
            value=time.fromisoformat(value).replace(tzinfo=timezone).localize(common.UTC)
        elif col=="days_supported":
            bitstring=0
            
            for day in value:
                bitstring |= (1 << DAY_TO_NUM[day])
            
            value=bitstring
        elif col=="services":
            value=common.toStringList(value)
            
        setattr(availability,col,value)
        
def reassign_or_cancel_bookings(session, availability):
    query=select(tables.Booking).where(tables.Booking.availability_parent_id==availability.id)
    for booking in session.scalars(query):
        sub_query=select(tables.Availability).where(get_availabilities_in_range(booking.start_datetime, booking.end_datetime, common.fromStringList(booking.services), booking.buisness)).limit(1)
        new_availability=session.scalars(sub_query).first()
        
        
        if (new_availability is not None) and (not check_for_conflict(session, booking.start_datetime, booking.end_datetime, booking.buisness)):
            booking.availability_parent_id=new_availability.id
        else:
            cancel_booking(session, booking)

def cancel_booking(session, booking):
    cancel_message=tables.Message()
    cancel_message.recipient=booking.author
    cancel_message.time_posted=datetime.now(common.UTC)
    cancel_message.title="Your booking got cancelled"
    cancel_message.text=f"Your booking {booking.id} got cancelled, as the buisness {booking.buisness} moved one of its availabilities out of the range. That's all we know."
    
    session.delete(booking)
    session.add(cancel_message)

def cancel_all_blocked_bookings(session, block):
    query=select(tables.Booking).where( (tables.Booking.buisness==block.author) & ((tables.Booking.start_datetime >= block.start_datetime) |  (tables.Booking.end_datetime <= block.end_datetime) ) ) #Coarse filter --- neccessary but not sufficient condition
    
    for booking in session.scalars(query).all():
        if block.time_period_contains(booking): #Maybe add has_service check later if buisnesses want to have a block for certain services?
            cancel_booking(session, booking)

def check_for_conflict(session, start_datetime, end_datetime, buisness, booking_id=None):
    query=select(tables.Availability.id).where(get_availabilities_in_range(start_datetime, end_datetime, [], buisness) & tables.Availability.available==False).limit(1) #May replace [] with common.fromStringList(booking.services) --- see similar comment in cancel_all_blocked_bookings
    if session.scalars(query).first() is not None:
        return True
    
    query=query=select(tables.Booking).where( (tables.Booking.buisness==buisness) & ((tables.Booking.start_datetime >= start_datetime) |  (tables.Booking.end_datetime <= end_datetime) ) & (tables.Booking.id != booking_id if booking_id is not None else true()) )
    
    return session.scalars(query).first() is not None
          
def get_availabilities_in_range(start_datetime, end_datetime, services, buisness=None):
    return tables.Availability.time_period_contains(start_datetime) & tables.Availability.time_period_contains(end_datetime) & or_(tables.Availability.has_service(service) for service in services) & (tables.Availability.author==buisness if buisness is not None else true())

def availability_change(request, method):
    result={}
    
    uid=request.json["uid"]
        
    with Session(common.database) as session:
        availability=getAvailability(request.get["id"], session)
        
        if availability is None:
            result["error"]="DOES_NOT_EXIST"
            return result
        elif uid!=availability.author:
             result["error"]="INSUFFICIENT_PERMISSION"
             return result
        
        if method=="edit":
            assign_json_to_availability(availability, request.json)
        elif method=="delete":
            session.delete(availability)
        
        session.commit()
        
        if availability.available:
            reassign_or_cancel_bookings(session,availability)
        else:
            cancel_all_blocked_bookings(session, availability)
        
        session.commit()
             
    return result