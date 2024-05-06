from utils.availabilities import check_for_conflict
from utils import tables
from utils import common
from utils.common import session
from sqlalchemy import select
from zoneinfo import ZoneInfo
from datetime import datetime

def assign_json_to_booking(booking, data, create):
    timezone=ZoneInfo(data.get("timezone","UTC"))
    
    business=data["business"]
    service=data["service"]

    for col in booking.__mapper__.attrs.keys():
        if col in data:
            value=data[col]
        else:
            continue

    
        if col in ["id","author","code","availability_to_service","business"]:
            continue
        elif col.endswith("_datetime"):
            value=common.convert_to_datetime(value, timezone)
        setattr(booking,col,value)
   
    query=select(tables.Availability_to_Service.id).join_from(tables.Availability_to_Service, tables.Availability, tables.Availability_to_Service.availability==tables.Availability.id).where(tables.Availability.time_period_contains(booking.start_datetime) & tables.Availability.time_period_contains(booking.end_datetime) & tables.Availability.has_service(service)).limit(1)

    availability_to_service=session.scalars(query).first()

    if (availability_to_service is None) or check_for_conflict(booking.start_datetime, booking.end_datetime, business, booking.id if create==False else None): #Don't create booking if there is a conflict
        return -1

    booking.availability_to_service=availability_to_service
    booking.timestamp=datetime.now(common.UTC)
