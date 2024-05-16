from utils import common, tables

from utils.common import app, session

from utils import services

from flask import request

@app.route("/services/create")
@common.authenticate
def create_service():
    result={}
    
    uid=request.json["uid"]
    
    service=tables.Service()

    service.business=uid
    services.assign_json(service, request.json)

    session.add(service)
    
    session.commit() #So we can get an id
    
                
    session.commit()

    return result

@app.route("/services/info")
def service_info():
    result={}
    
    service=session.get(tables.Service, request.json["id"])
    
    if service is None:
        result["error"]="NOT_FOUND"
        return result
    
    for col in service.__mapper__.attrs.keys():
        value=getattr(service,col)
        if col=="id":
            continue                
        result[col]=value
        
    return result

@app.route("/services/edit")
@common.authenticate
def service_edit(): #Have to reassign all availbility that is attached to service     
    return services.modify(request, "edit")

@app.route("/services/delete")
@common.authenticate
def service_delete():     
    return services.modify(request, "delete")
