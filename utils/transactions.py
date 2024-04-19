from utils import tables, balance
from sqlalchemy import select
from utils import common, tables
from datetime import datetime
from zoneinfo import ZoneInfo

def getTransaction(transaction_id, session=None):
    return common.getItem(tables.Transaction, transaction_id, session)

def assign_json_to_transaction(session, transaction, data, create):
    timezone = ZoneInfo(data.get("timezone", "UTC"))

    for col in transaction.__mapper__.attrs.keys():
        if col in data:
            value = data[col]
        else:
            continue

        if col in ["id", "booking"]:
            continue
        elif col == "timestamp":
            value = datetime.strptime(value, common.DATETIME_FORMAT).replace(tzinfo=timezone).astimezone(common.UTC)
        setattr(transaction, col, value)

def price_of_booking(session,booking):
    query=select(tables.Service.price).join_from(tables.Availability_to_Service, tables.Service, tables.Availability_to_Service.service==tables.Service.id).where(tables.Availability_to_Service.id==booking.availability_to_service)

    price=session.scalars(query).first()
    return price
                                       
def create(session,booking):
    id=booking.author
    bal=session.get(tables.Balance, id)
    if not bal:
        return -1
    ret=balance.RemoveFromBalance(id, price_of_booking(session,booking))

    if not ret:
        return -1

def refund(session,booking):
    balance.AddToBalance(id, price_of_booking(session,booking))