import utils.common as common
import utils.tables as tables
from sqlalchemy import or_, true

def getAvailability(availability_id,session=None):
    return common.getItem(tables.Availability,availability_id,session)

def assign_json_to_availability(availabilitiy, data):
    timezone=ZoneInfo(data.get("timezone","UTC"))
    for col in availability.__mapper__.attrs.keys():
        if col in data:
            value=data[col]
        else:
            continue
        
        if col in ["id","author"]:
            continue
        if col.endswith("_datetime"):
            value=datetime.strptime(value, DATETIME_FORMAT).replace(tzinfo=timezone).localize(UTC)
        elif col.endswith("_time"):
            value=time.fromisoformat(value).replace(tzinfo=timezone).localize(UTC)
        elif col=="days_supported":
            bitstring=0
            
            for day in value:
                bitstring |= (1 << day_to_num[day])
            
            value=bitstring
        elif col=="services":
            value=common.toStringList(value)
            
        setattr(availability,col,value)
        
def reassign_or_cancel_bookings(session, availability):
    query=select(table.Bookings).where(tables.Bookings.availability_parent_id==availability.id)
    for booking in session.scalars(query):
        new_availabilities=get_availabilities_in_range(session, booking.start_datetime, booking.end_datetime, common.fromStringList(booking.services), buisness=booking.buisness) #Optional buisness id to filter by
    
        if len(new_availabilities)>0:
            booking.availability_parent_id=new_availabilities[0].id
        else:
            cancel_post=tables.Message()
            cancel_post.recipient=booking.author
            cancel_post.time_posted=datetime.now(UTC)
            cancel_post.title="Your booking got cancelled"
            cancel_post.text=f"Your booking {booking.id} got cancelled, as the buisness {booking.buisness} moved one of its availabilities out of the range. That's all we know"
            
            session.delete(booking)
            session.add(cancel_post)
            
def get_availabilities_in_range(session, start_datetime, end_datetime, services, buisness=None):
    query=select(tables.Availability).where(tables.Availability.time_period_contains(start_datetime) & tables.Availability.time_period_contains(end_datetime) & or_(tables.Availability.has_service(service) for service in services) & (tables.Availability.author==buisness if buisness is not None else true())).distinct()
    
    return session.query(query).all()

def availability_edit(request, method):
    result={}
    
    uid=request.json["uid"]
    user=users.getUser(uid)
        
    with Session(common.database) as session:
        availability=availabilities.getAvailability(request.get["id"], session)
        if availability is None:
            result["error"]="DOES_NOT_EXIST"
            return result
        elif uid!=availability.author:
             result["error"]="INSUFFICIENT_PERMISSION"
             return result
        
        if method=="edit":
            availabilities.assign_json_to_availability(availability, request.json)
        elif method=="delete":
            session.delete(availability)
        
        session.commit()
        availabilities.reassign_or_cancel_bookings(session,availability)
        
        session.commit()
             
    return result