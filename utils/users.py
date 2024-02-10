from utils import tables, common

def getUser(user_id,session=None):
    return common.getItem(tables.User,user_id,session)