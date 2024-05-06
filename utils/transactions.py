from utils import tables, balance
from sqlalchemy import select
from utils.common import session

def price_of_booking(session,booking):
    query=select(tables.Service.price).join_from(tables.Availability_to_Service, tables.Service, tables.Availability_to_Service.service==tables.Service.id).where(tables.Availability_to_Service.id==booking.availability_to_service)

    price=session.scalars(query).first()
    return price
                                       
def create(booking):
    id=booking.author
    bal=session.get(tables.Balance, id)
    if not bal:
        return -1
    ret=balance.RemoveFromBalance(id, price_of_booking(session,booking))

    if not ret:
        return -1

def refund(booking):
    id=booking.author
    balance.AddToBalance(id, price_of_booking(session,booking))

