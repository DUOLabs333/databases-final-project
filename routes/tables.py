from utils import common, tables

from utils.common import app, session

from flask import request

from faker import Faker
import string, datetime
from datetime import UTC
import threading

tables_lock=threading.Lock()

MAX_DATETIME=datetime.datetime.max.replace(tzinfo=UTC)
NUM_ROWS=100
REPETITIONS=["ONETIME","DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
DEVICES=["IPHONE", "IPAD", "MACBOOK", "PIXEL", "HTC", "SAMSUNG", "XIAOMI"] #We can get more specific later
REPAIRS=["SCREEN_REPAIR", "CAMERA_REPAIR", "BATTERY_REPLACEMENT"]

VEHICLES=["TOYOTA", "BMW", "VOLKSWAGEN"]
SERVICES=["DETAILING", "GENERAL_WASH","BRAKE_FLUID"]

@app.route("/tables/populate")
@common.authenticate
def populate():
    result={}
    faker=Faker()

    def random_price():
        return round(faker.pyfloat(min_value=0),2)

    """
    By default, it is localized to US English (ie, "en_US"), but in the future, we could randomize the locale when generating data.
    
    However, if we do so, we would need another attribute for tables.User; namely, country_code, which will default to "US". 
    
    This will be useful for two reasons --- one, when searching for availabilities, we can filter the results to only match the country code of the user searching (which will also mean that availabilities/search will require login) --- this makes sense as you likely don't want to visit a shop in another country.

    Additionally, we can use the country code when calculating distance --- right now, it is hardcoded to the US, but that can obviously change, so we need to be able to dynamically set the country when calculating distances
    """
    uid=request.json["uid"]

    if uid!=-1:
        result["error"]="INSUFFICIENT_PERMISSION"
        return result
    
    with tables_lock:
        tables.BaseTable.metadata.create_all(common.database,checkfirst=True) #Create tables if they don't exist

        users_list=[]
        availabilities_list=[]
        services_list=[]
        availability_to_service_list=[]

        for _ in range(NUM_ROWS):   
            user=tables.User()
            
            user.id=faker.unique.pyint(min_value=1)
            users_list.append(user.id)
            
            user.username=faker.unique.name().replace(" ","") #Lazy version of faker.unique.simple_profile()["username"] --- couldn't use that piece of code as unique saves the elements in a set to prevent repeats. However, simple_profile() returns dictionaries, which can not be added to sets
            user.password_hash=''.join(faker.random_elements(elements=string.ascii_letters+string.digits, length=64, unique=False))
            user.password_salt=common.generate_salt()
            user.creation_time=faker.date_time(tzinfo=UTC)
            user.profile=faker.paragraph(nb_sentences=5)
            user.address=faker.unique.address().replace("\n",", ")
            user.zip_code=faker.postcode()
            
            session.add(user)

        for _ in range(NUM_ROWS):

            message=tables.Message()
            message.recipient=faker.random_element(elements=users_list)
            message.time_posted=faker.date_time(tzinfo=UTC)
            message.title=faker.text(max_nb_chars=80)
            message.text=faker.paragraph(nb_sentences=5)
            
            session.add(message)

        for _ in range(NUM_ROWS):
            availability=tables.Availability()
            
            availability.id=faker.unique.pyint()
            availabilities_list.append(availability.id)
            
            if(request.json.get("disable_conflicts",True)):
                availability.available=True #No availability is a block
            else:
                availability.available=faker.pybool()

            availability.business=faker.random_element(elements=users_list)
            availability.start_datetime=faker.date_time(tzinfo=UTC)
            availability.end_datetime=faker.date_time_between(start_date=availability.start_datetime, end_date=MAX_DATETIME)
            availability.days_supported=faker.pyint(max_value=2**7-1)

            times=[faker.time_object(), faker.time_object()]
            times.sort() #start_time should be earlier than end_time

            availability.start_time=times[0]
            availability.end_time=times[1]


            availability.repetition=faker.random_element(elements=REPETITIONS)
            
            session.add(availability)

        for _ in range(NUM_ROWS):
            service=tables.Service()
            service.id=faker.unique.pyint()
            service.business=faker.random_element(elements=users_list)
            services_list.append(service.id)
            service.price=random_price()
            is_repair=faker.pybool()
            if is_repair:
                service.device=faker.random_element(elements=DEVICES)
                service.device_repair=faker.random_element(elements=REPAIRS)
            else:
                service.vehicle=faker.random_element(elements=VEHICLES)
                service.vehicle_service=faker.random_element(elements=SERVICES)
            session.add(service)

        for _ in range(NUM_ROWS):
            availability_to_service=tables.Availability_to_Service()
            availability_to_service.id=faker.unique.pyint()
            availability_to_service_list.append(availability_to_service.id)
            availability_to_service.availability=faker.random_element(elements=availabilities_list)
            availability_to_service.service=faker.random_element(elements=services_list)
            session.add(availability_to_service)

        for _ in range(NUM_ROWS):
            if (request.json.get("disable_conflicts",True)):
                continue #Can't conflict with bookings that don't exist

            booking=tables.Booking()
            booking.author=faker.random_element(elements=users_list)
            booking.cost=random_price()
            
            booking.availability_to_service=faker.random_element(elements=availability_to_service_list)
            booking.start_datetime=faker.date_time(tzinfo=UTC)
            booking.end_datetime=faker.date_time_between(start_date=booking.start_datetime, end_date=MAX_DATETIME)
            booking.code=faker.unique.pyint(max_value=1000000)
            
            session.add(booking)
        
        for uid in users_list: #Initialize balance for all test users
            balance=tables.Balance()
            balance.id=uid
            balance.balance=random_price()
            session.add(balance)

        #We don't populate the Transactions and Uploads tables currently
        session.commit()
    return result

@app.route("/tables/drop")
@common.authenticate
def drop():
    result={}
    
    uid=request.json["uid"]
    if uid!=-1:
        result["error"]="INSUFFICIENT_PERMISSION"
        return result
    with tables_lock:
        tables.BaseTable.metadata.drop_all(common.database, checkfirst=True)
        session.commit()

    return result

import csv, io
from zoneinfo import ZoneInfo
from flask import send_file
from sqlalchemy import select 

@app.route("/tables/export")
@common.authenticate
def tables_export():
    if request.json["uid"]!=common.ROOT_UID:
        return {"error": "INSUFFICIENT_PERMISSION"}
    
    timezone=ZoneInfo(request.json.get("timezone","UTC"))
    start_datetime=common.convert_to_datetime(request.json["start_datetime"], timezone)
    end_datetime=common.convert_to_datetime(request.json["end_datetime"], timezone)


    keys=tables.Transaction.__mapper__.attrs.keys()
    buffer=io.BytesIO()
    writer=csv.DictWriter(io.TextIOWrapper(buffer,encoding="utf-8",newline="",line_buffering=True, write_through=True), fieldnames=keys)
    writer.writeheader()

    query=select(tables.Transaction).where((tables.Transaction.timestamp >= start_datetime) & (tables.Transaction.timestamp <= end_datetime))

    for row in session.scalars(query):
        writer.writerow({key: getattr(row, key) for key in keys})

    buffer.seek(0)


    return send_file(buffer, mimetype="test/csv", as_attachment=True, download_name=f"transactions_{common.convert_from_datetime(start_datetime, common.UTC)}_{common.convert_from_datetime(end_datetime, common.UTC)}.csv")
