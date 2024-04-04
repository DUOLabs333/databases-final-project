import utils.common as common
import utils.tables as tables
import utils.availabilities as availabilities

from sqlalchemy import select
from sqlalchemy.orm import Session

def assign_json(service, data):
    for col in service.__mapper__.attrs.keys():
        if col in data:
            value=data[col]
        else:
            continue
        
        if col in ["id","buisness"]:
            continue
          
        setattr(service,col,value)
        

def modify(request, method):
    result={}
    
    uid=request.json["uid"]
        
    with Session(common.database) as session:
        service=session.get(tables.Service, request.get["id"])
        
        if service is None:
            result["error"]="DOES_NOT_EXIST"
            return result
        elif uid!=service.buisness:
             result["error"]="INSUFFICIENT_PERMISSION"
             return result
        
        if method=="edit":
            assign_json(service, request.json)
        elif method=="delete":
            session.delete(service)

        session.commit() #Push the changes that we made so that future calls to the database can see this
        query=select(tables.Availability_to_Service.availability).where(tables.Availability_to_Service.service==service.id)

        for availability in session.scalars(query): #Since service has changed, any availability attached to it may become invalid to bookings
            availabilities.reassign_or_cancel_bookings(session,availability)

        session.commit()
             
    return result
