from utils import common, tables

from utils.common import app

from sqlalchemy.orm import Session

from flask import request

from faker import Faker as faker
import string, datetime
from datetime import UTC

MAX_DATETIME=datetime.datetime().max.replace(tzinfo=UTC)
NUM_ROWS=100
REPETITIONS=["ONETIME","DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
DEVICES=["IPHONE", "IPAD", "MACBOOK", "PIXEL", "HTC", "SAMSUNG", "XIAOMI"] #We can get more specific later
REPAIRS=["SCREEN_REPAIR", "CAMERA_REPAIR", "BATTERY_REPLACEMENT"]

VEHICLES=["TOYOTA", "BMW", "VOLKSWAGEN"]
SERVICES=["DETAILING", "GENERAL_WASH","BRAKE_FLUID"]

@app.route("/tables/populate")
def populate():
    result={}
    
    uid=request.json["uid"]
    if uid!=0:
        result["error"]="INSUFFICIENT_PERMISSION"
        return result
    
    with Session(common.database) as session:
        user=tables.User()
        user.id=0
        user.username="root"
        user.password_hash="root" #Insecure, but I don't care enough
        user.creation_time=datetime.now(UTC)
        session.add(user)
        
        users_list=[0]
        availabilities_list=[]
        services_list=[]
        availability_to_service_list=[]

        for i in range(NUM_ROWS): #Technically, each table population procedure should be in its own loop --- otherwise, the probability distributions of foreign keys like availability.buisness is not uniform, but are biased towards the first ids created   
            user=tables.User()
            
            user.id=faker.unique.pyint(min_value=1)
            users_list.append(user.id)
            
            user.username=faker.unique.simple_profile()["username"]
            user.password_hash=''.join(faker.random_elements(elements=string.ascii_letters+string.digits, length=64, unique=False))
            user.creation_time=faker.date_time(tzinfo=UTC)
            user.profile=faker.paragraph(nb_sentences=5)
            user.address=faker.unique.address().replace("\n",", ")
            user.zip_code=faker.postcode()
            
            session.add(user)
            
            message=tables.Message()
            message.recipient=faker.random_element(elements=users_list)
            message.time_posted=faker.date_time(tzinfo=UTC)
            message.title=faker.text(max_nb_chars=80)
            message.text=faker.paragraph(nb_sentences=5)
            
            session.add(message)
            
            availability=tables.Availability()
            
            availability.id=faker.unique.pyint()
            availabilities_list.append(availability.id)
            
            availability.available=faker.pybool()
            availability.author=faker.random_element(elements=users_list)
            availability.start_datetime=faker.date_time(tzinfo=UTC)
            availability.end_datetime=faker.date_time_between(start_date=availability.start_datetime, end_date=MAX_DATETIME)
            availability.days_supported=faker.pyint(max_value=2**7-1)
            availability.start_time=faker.time_object()
            availability.end_time=faker.time_object()
            availability.repetition=faker.random_element(elements=REPETITIONS)
            availability.services=common.toStringList(faker.random_choices(SERVICES))
            
            session.add(availability)
            
            service=tables.Service()
            service.id=faker.unique.pyint()
            services_list.append(service.id)
            service.price=faker.pyfloat()
            is_repair=faker.random_bool()
            if is_repair:
                service.device=faker.random_element(elements=DEVICES)
                service.repair=faker.random_element(elements=REPAIRS)
            else:
                service.vehicle=faker.random_element(elements=VEHICLES)
                service.vehicle_service=faker.random_element(elements=SERVICES)
            session.add(service)

            availability_to_service=tables.Availability_to_Service()
            availability_to_service.id=faker.unique.pyint()
            availability_to_service_list.append(availability_to_service.id)
            availability_to_service.availability=faker.random_element(elements=availabilities_list)
            availability_to_service.service=faker.random_element(elements=services_list)
            session.add(availability_to_service)

            booking=tables.Booking()
            booking.author=faker.random_element(elements=users_list)
            
            booking.availability_to_service=faker.random_element(elements=availability_to_service_list)
            booking.start_datetime=faker.date_time(tzinfo=UTC)
            booking.end_datetime=faker.date_time_between(start_date=booking.start_datetime, end_date=MAX_DATETIME)
            booking.code=faker.unique.pyint(maxint=1000000)
            
            session.add(booking)
        
        #We don't populate the Transactions or Uploads tables currently
        session.commit()
    return result

@app.route("/tables/drop")
def drop():
    result={}
    
    uid=request.json["uid"]
    if uid!=0:
        result["error"]="INSUFFICIENT_PERMISSION"
        return result
    
    with Session(common.database) as session:
        tables.User.metadata.drop_all()
        session.commit()
    return result
