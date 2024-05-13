from utils import tables, balance
from utils.common import session
from utils import common
from datetime import datetime

def _create(from_id, to_id, amount): #Internal implementation
    if (amount==0) or (to_id==from_id):
        return

    if not (session.get(tables.Balance, from_id) and session.get(tables.Balance, to_id)):
        return -1
    
    transaction=tables.Transaction()

    transaction.sender=from_id
    transaction.recipient=to_id
    transaction.amount=amount

    ret=balance.RemoveFromBalance(transaction.sender, transaction.amount)
    if not ret:
        return -1

    ret=balance.AddToBalance(transaction.recipient, transaction.amount)

    transaction.timestamp=datetime.now(common.UTC)
    session.add(transaction)
    session.commit()


    
def create(booking, amount):
    user_id=booking.author
    business_id=session.get(tables.Availability, session.get(tables.Availability_to_Service, booking.availability_to_service).availability).business

    
    if amount < 0: #Refunds
        ret=_create(business_id, user_id, -amount) #We (RepairWave) do not incur additional charges from refunds
    else:
        if _create(user_id, common.ROOT_UID, amount)==-1:
            return -1
        
        ret=_create(common.ROOT_UID, business_id, 0.9*amount) #We keep 10% of the revenue from transactions
    if ret==-1:
        return -1

def refund(booking):
    return create(booking, -booking.cost)
