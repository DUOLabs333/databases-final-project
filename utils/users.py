from utils import tables, common

def getUser(user_id,session=None):
    return common.getItem(tables.User,user_id,session)

def checkIfUsernameExists(username): #You must have the USERS database locked, and you must not unlock it until you placed the (new) username into the database
    with Session(common.database) as session:
        return session.scalars(select(tables.User.id).where(tables.User.username==username)).first() is not None