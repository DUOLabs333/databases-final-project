from utils import common, tables

from utils.common import app

from sqlalchemy.orm import Session

from flask import request

from faker import Faker
fake=Faker()

@app.route("/users/info")
def populate():
    result={}
    
    uid=request.json["uid"]
    if uid!=0:
        result["error"]="INSUFFICIENT_PERMISSION"
        return result
    
    with Session(common.database) as session:
        pass
    