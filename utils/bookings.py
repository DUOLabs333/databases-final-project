from utils.availabilities import check_for_conflict
from utils import tables, common, transactions
from utils.common import session
from zoneinfo import ZoneInfo
from datetime import datetime

def assign_json_to_booking(booking, data):
    timezone=ZoneInfo(data.get("timezone","UTC"))

    for col in booking.__mapper__.attrs.keys():
        if col in data:
            value=data[col]
        else:
            continue

    
        if col in ["id","author","code","business"]:
            continue
        elif col.endswith("_datetime"):
            value=common.convert_to_datetime(value, timezone)
        setattr(booking,col,value)
    
    if not booking.id:
        old_cost=0

    availability_to_service=session.get(tables.Availability_to_Service, booking.availability_to_service)

    availability=session.get(tables.Availability, availability_to_service.availability)
    business=availability.business

    service=session.get(tables.Service, availability_to_service.service)
    booking.cost=service.price
    cost=booking.cost-old_cost

    
    ret=transactions.create(booking, cost)
    if ret==-1:
        return ret

    if check_for_conflict(booking.start_datetime, booking.end_datetime, business, booking.id): #Don't create booking if there is a conflict
        return -1
    
    booking.timestamp=datetime.now(common.UTC)
