from utils.availabilities import check_for_conflict
from utils import common, tables
from sqlalchemy import select
from zoneinfo import ZoneInfo
from datetime import datetime

def getBooking(booking_id,session=None):
    return common.getItem(tables.Booking,booking_id,session)
    
def assign_json_to_booking(session, booking, data, create):
    timezone=ZoneInfo(data.get("timezone","UTC"))
    
    buisness=data["buisness"]
    service=data["service"]

    for col in booking.__mapper__.attrs.keys():
        if col in data:
            value=data[col]
        else:
            continue

    
        if col in ["id","author","code","service","buisness"]:
            continue
        elif col.endswith("_datetime"):
            value=datetime.strptime(value, common.DATETIME_FORMAT).replace(tzinfo=timezone).localize(common.UTC)
        setattr(booking,col,value)
   
    query=select(tables.Availability_to_Service.id).join_from(tables.Availability_to_Service, tables.Availability).where(tables.Availability.time_period_contains(booking.start_datetime) & tables.Availability.time_period_contains(booking.end_datetime) & tables.Availability.has_service(service)).limit(1)

    availability_to_service=session.scalars(query).first()

    if (availability_to_service is None) or check_for_conflict(session, booking.start_datetime, booking.end_datetime, buisness, booking.id if create==False else None): #Don't create booking if there is a conflict
        return -1

    booking.availability_to_service=availability_to_service
