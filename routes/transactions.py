from utils import common, tables, transactions
from flask import request
from sqlalchemy.orm import Session

@app.route("/transactions/create", methods=["POST"])
@common.authenticate
def create_transaction():
    result = {}
    uid = request.json["uid"]
    with Session(common.database) as session:
        transaction = tables.Transaction()
        session.add(transaction)
        
        # Assume transaction data includes 'booking' which links to a booking ID
        transaction.booking = request.json.get('booking')
        ret = transactions.assign_json_to_transaction(session, transaction, request.json, True)
        
        if ret == -1:
            session.remove(transaction)
            result["error"] = "BLOCKED"
            return result
        
        session.commit()
    
    return result

@app.route("/transactions/info", methods=["GET"])
@common.authenticate
def transaction_info():
    result = {}
    uid = request.json["uid"]
    with Session(common.database) as session:
        transaction = transactions.getTransaction(request.json["id"], session=session)
        
        if transaction is None:
            result["error"] = "DOES_NOT_EXIST"
            return result
        
        # Assuming 'booking' field links to Booking and includes 'author' and possibly 'business'
        booking = session.get(tables.Booking, transaction.booking)
        
        if uid not in [booking.author, booking.business]:
            result["error"] = "INSUFFICIENT_PERMISSION"
            return result
        
        for col in transaction.__mapper__.attrs.keys():
            value = getattr(transaction, col)
            result[col] = value
        
    return result

@app.route("/transactions/update", methods=["PUT"])
@common.authenticate
def update_transaction():
    result = {}
    uid = request.json["uid"]
    with Session(common.database) as session:
        transaction = transactions.getTransaction(request.json["id"], session=session)
        
        if transaction is None:
            result["error"] = "DOES_NOT_EXIST"
            return result
        
        ret = transactions.assign_json_to_transaction(session, transaction, request.json, False)
        
        if ret == -1:
            result["error"] = "BLOCKED"
            return result
        
        session.commit()
    
    return result

@app.route("/transactions/delete", methods=["DELETE"])
@common.authenticate
def delete_transaction():
    result = {}
    uid = request.json["uid"]
    with Session(common.database) as session:
        transaction = transactions.getTransaction(request.json["id"], session=session)
        
        if transaction is None:
            result["error"] = "DOES_NOT_EXIST"
            return result
        
        session.delete(transaction)
        session.commit()
    
    return result

@app.route("/transactions/list", methods=["GET"])
@common.authenticate
def transaction_list():
    result = {}
    uid = request.json["uid"]
    with Session(common.database) as session:
        # Example: List transactions for a specific booking
        booking_id = request.json.get("booking_id")
        query = session.query(tables.Transaction).filter_by(booking=booking_id)
        
        transactions_list = query.all()
        result["transactions"] = [{
            "id": trans.id,
            "method": trans.method,
            "status": trans.status,
            "timestamp": trans.timestamp.isoformat()
        } for trans in transactions_list]
        
    return result
