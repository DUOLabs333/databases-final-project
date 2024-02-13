from utils.availabilities import check_for_conflict
from utils import common, tables

from zoneinfo import ZoneInfo
from datetime import datetime

def getBooking(booking_id,session=None):
    return common.getItem(tables.Booking,booking_id,session)
    
def assign_json_to_booking(session, booking, data, create):
    timezone=ZoneInfo(data.get("timezone","UTC"))
    
    for col in booking.__mapper__.attrs.keys():
        if col in data:
            value=data[col]
        else:
            continue
        
        if col in ["id","author","code"]:
            continue
        elif col=="services":
            value=common.toStringList(value)
        elif col.endswith("_datetime"):
            value=datetime.strptime(value, common.DATETIME_FORMAT).replace(tzinfo=timezone).localize(common.UTC)
        setattr(booking,col,value)
    
    if check_for_conflict(session, booking.start_datetime, booking.end_datetime, booking.buisness, booking.id if create==False else None):
        return -1