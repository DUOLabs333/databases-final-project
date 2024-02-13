from utils import tables, common
from sqlalchemy import select
from sqlalchemy.orm import Session

def getUser(user_id,session=None):
    return common.getItem(tables.User,user_id,session)

def checkIfUsernameExists(username): #You must have the USERS database locked, and you must not unlock it until you placed the (new) username into the database
    with Session(common.database) as session:
        return session.scalars(select(tables.User.id).where(tables.User.username==username)).first() is not None


def assign_json_to_user(user, data):
    for col in user.__mapper__.attrs.keys():
        if col not in data:
            continue
        if col in ["id", "creation_time"]:
            continue
        
        setattr(user,col,data[col])