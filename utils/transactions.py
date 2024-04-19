from utils import common, tables
from datetime import datetime
from zoneinfo import ZoneInfo

def getTransaction(transaction_id, session=None):
    return common.getItem(tables.Transaction, transaction_id, session)

def assign_json_to_transaction(session, transaction, data, create):
    timezone = ZoneInfo(data.get("timezone", "UTC"))

    for col in transaction.__mapper__.attrs.keys():
        if col in data:
            value = data[col]
        else:
            continue

        if col in ["id", "booking"]:
            continue
        elif col == "timestamp":
            value = datetime.strptime(value, common.DATETIME_FORMAT).replace(tzinfo=timezone).astimezone(common.UTC)
        setattr(transaction, col, value)