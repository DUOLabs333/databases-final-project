from utils import common, tables

from utils.common import app

from sqlalchemy.orm import Session

from flask import request

from faker import Faker as faker
import string, datetime, itertools
from datetime import UTC

MAX_DATETIME=datetime.datetime().max.replace(tzinfo=UTC)
NUM_ROWS=100
REPETITIONS=["ONETIME","DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
DEVICES=["IPHONE", "IPAD", "MACBOOK", "PIXEL", "HTC", "SAMSUNG", "XIAOMI"] #We can get more specific later
REPAIRS=["SCREEN_REPAIR", "CAMERA_REPAIR", "BATTERY_REPLACEMENT"]

SERVICES=[",".join(_) for _ in itertools.product(DEVICES, REPAIRS)]

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
        
        #Make sure appointments don't have end_datetime that is before start_datetime
        #Get services from a predefined list --- in format "DEVICE,SERVICE "...
        for i in range(NUM_ROWS):
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
            
            availabilities_list=[]
            availability=tables.Availability()
            
            availability.id=faker.unique.pyint()
            availabilities_list.append(availability.id)
            
            availability.author=faker.random_element(elements=users_list)
            availability.start_datetime=faker.date_time(tzinfo=UTC)
            availability.end_datetime=faker.date_time_between(start_date=availability.start_datetime, end_date=MAX_DATETIME)
            availability.days_supported=faker.pyint(max_value=2**7-1)
            availability.start_time=faker.time_object()
            availability.end_time=faker.time_object()
            availability.repetition=faker.random_element(elements=REPETITIONS)
            availability.services=common.toStringList(faker.random_choices(SERVICES))
            
            session.add(availability)
            
            booking=tables.Booking()
            booking.author=faker.random_element(elements=users_list)
            booking.buisness=faker.random_element(elements=users_list)
            booking.services=faker.random_element(elements=SERVICES)
            booking.start_datetime=faker.date_time(tzinfo=UTC)
            booking.end_datetime=faker.date_time_between(start_date=booking.start_datetime, end_date=MAX_DATETIME)
            booking.availability_parent_id=faker.random_element(elements=availabilities_list)
            booking.code=faker.unique.pyint(maxint=1000000)
            
            session.add(booking)
        
        session.commit()
    return result

@app.route("/tables/drop")
def populate():
    result={}
    
    uid=request.json["uid"]
    if uid!=0:
        result["error"]="INSUFFICIENT_PERMISSION"
        return result
    
    with Session(common.database) as session:
        tables.User.metadata.drop_all()
        session.commit()
    return result