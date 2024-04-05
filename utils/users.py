from utils import tables, common
from sqlalchemy import select
from sqlalchemy.orm import Session

def checkIfUsernameExists(username): #You must have the USERS database locked, and you must not unlock it until you placed the (new) username into the database
    with Session(common.database) as session:
        return session.scalars(select(tables.User.id).where(tables.User.username==username)).first() is not None

def assign_json_to_user(user, data):
    for col in user.__mapper__.attrs.keys():
        if col=="password":
            user.password_hash=common.pass_hash(data["password"], user.password_salt)
            continue
        if col not in data:
            continue
        if col in ["id", "creation_time","password_salt"]:
            continue
        
        setattr(user,col,data[col])
