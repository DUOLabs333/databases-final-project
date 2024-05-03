from utils import tables, transactions
from sqlalchemy import true, select
from zoneinfo import ZoneInfo
from datetime import datetime, time
from utils.common import session
from utils import common

DAY_TO_NUM={"MONDAY":0, "TUESDAY":1, "WEDNESDAY":2, "THURSDAY":3, "FRIDAY":4, "SATURDAY":5, "SUNDAY":6}

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
            query=select(tables.Availability_to_Service.service).where(tables.Availability_to_Service.service==availability.id)
            old_services=set(session.scalars(query).all()) #The existing services attached to the availability
            new_services=set(value) #What services should be attached to the availability

            to_be_added=new_services-old_services
            to_be_deleted=old_services - new_services

            for service in to_be_added: #Add new rows for every new service
                row=tables.Availability_to_Service()
                row.availability=availability.id
                row.service=service
                session.add(row)

            query=select(tables.Availability_to_Service).where(tables.Availability_to_Service.availability==availability.id & tables.Availability_to_Service.service.in_(to_be_deleted))
            for row in session.scalars(query): #Delete all rows which is attached to the no-longer-attached services
                session.delete(row)

            session.commit()
            continue
            
        setattr(availability,col,value)
        
def reassign_or_cancel_bookings(availability): #Handle all bookings that are currently attached to an availability (availability may be deleted or edited, so all child bookings have to be upgraded to match)
    query=select(tables.Booking).join(tables.Availability_to_Service, tables.Booking.availability_to_service==tables.Availability_to_Service.id).where((tables.Availability_to_Service.availability==availability.id) & (tables.Booking.start_datetime < datetime.now(common.UTC))) #Get all bookings that use <availability>
    
    for booking in session.scalars(query):
        service=session.get(tables.Service, session.get(tables.Availability_to_Service, booking.availability_to_service).service).services_dict #Get dictionary representing the service that the booking is booked for

        sub_query=select(tables.Availability_to_Service).where(get_availabilities_in_range(booking.start_datetime, booking.end_datetime, service, availability.business)).limit(1) #Get the first availability that matches the booking's services

        new_availability=session.scalars(sub_query).first()
        
        
        if (new_availability is not None) and (not check_for_conflict(booking.start_datetime, booking.end_datetime, availability.business)): #If such an availability exists and does not conflict with any blocks/other bookings
            booking.availability_to_service=new_availability.id
        else:
            cancel_booking(booking) #No way to keep the booking

def cancel_booking(booking):                                                            
    cancel_message=tables.Message()
    cancel_message.recipient=booking.author
    cancel_message.time_posted=datetime.now(common.UTC)
    cancel_message.title="Your booking got cancelled"
    cancel_message.text=f"Your booking {booking.id} got cancelled, as the business {booking.business} moved one of its availabilities out of the range. That's all we know."
    
    session.delete(booking)
    session.add(cancel_message)
    transactions.refund(booking)

def cancel_all_blocked_bookings(block): #Cancel all bookings that conflict with block
    query=select(tables.Booking).where((tables.Booking.business==block.business) & ((tables.Booking.start_datetime >= block.start_datetime) |  (tables.Booking.end_datetime <= block.end_datetime) ) ) #Coarse filter --- neccessary but not sufficient condition (also lets me avoid remaking all of the availability-matching code)
    
    for booking in session.scalars(query).all():
        if block.time_period_contains(booking): #Maybe add has_service check later if businesses want to have a block for certain services?
            cancel_booking(booking)

def check_for_conflict(start_datetime, end_datetime, business, booking_id=None):
    query=select(tables.Availability.id).where(get_availabilities_in_range(start_datetime, end_datetime, {}, business, available=False)).limit(1) #See if there's a block that conflicts with the proposed time period

    if session.scalars(query).first() is not None:
        return True
    
    query=select(tables.Booking).where( (tables.Booking.business==business) & ((tables.Booking.start_datetime >= start_datetime) |  (tables.Booking.end_datetime <= end_datetime) ) & (tables.Booking.id != booking_id if booking_id is not None else true()) ) #See if there's any other booking that conflicts with the time period
    
    return session.scalars(query).first() is not None
          
def get_availabilities_in_range(start_datetime, end_datetime, services, business=None, available=True): #Should work --- since bookings must take place within one day, and availabilities on the same day are contiguous, if two points are within the availability, then availability exists between them (Intermediate value theorem)
    
    return tables.Availability.time_period_contains(start_datetime) & tables.Availability.time_period_contains(end_datetime) & tables.Availability.has_service(services) & (tables.Availability.business==business if business is not None else true()) & (tables.Availability.available==available)

def availability_change(request, method):
    result={}
    
    uid=request.json["uid"]
        
    availability=session.get(tables.Availability, request.json["id"])
    
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

    session.commit() #Push the changes that we made so that future calls to the database can see this
    if not((not availability.available) and (method=="delete")): #We don't have to consider what happens when you delete a block, as there's no way that availability can decrease 
        reassign_or_cancel_bookings(availability)

    session.commit()
             
    return result
