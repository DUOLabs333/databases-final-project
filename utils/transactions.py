from utils import tables, balance
from utils.common import session, UTC
from datetime import datetime

def create(booking, amount):
    if amount==0:
        return
    
    user_id=booking.author
    business_id=session.get(tables.Availability, session.get(tables.Availability_to_Service, booking.availability_to_service).availability).business

    if not (session.get(tables.Balance, user_id) and session.get(tables.Balance, business_id)):
        return -1

    transaction=tables.Transaction()
    if amount < 0: #Maybe set it up so that refunds to not incur an additional penalty on the business
        transaction.sender=business_id
        transaction.recipient=user_id
        transaction.amount=-amount
    else:
        transaction.sender=user_id
        transaction.recipient=business_id
        transaction.amount=amount
    ret=balance.RemoveFromBalance(transaction.sender, transaction.amount)
    if not ret:
        return -1

    ret=balance.AddToBalance(transaction.recipient, transaction.amount)
    
    transaction.timestamp=datetime.now(UTC)
    session.add(transaction)
    session.commit()

def refund(booking):
    return create(booking, -booking.cost)
