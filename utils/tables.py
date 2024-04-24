from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy import ForeignKey, case, true, select, inspect, extract
from sqlalchemy.types import DateTime
from datetime import datetime as Datetime
from datetime import time as Time
import datetime
from zoneinfo import ZoneInfo
from utils.common import session

# declarative base class
class BaseTable(DeclarativeBase):
    pass

class User(BaseTable):
    __tablename__ = "USERS"

    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    password_salt: Mapped[str]
    creation_time: Mapped[Datetime]
    profile: Mapped[str] = mapped_column(default="")
    address: Mapped[str] = mapped_column(default="")
    zip_code: Mapped[str] = mapped_column(default="")
    avatar: Mapped[int] = mapped_column(ForeignKey("UPLOADS.id"), nullable=True)
        
                
class Message(BaseTable): #Holds administrative messages and notifications of people booking service
    __tablename__ = "MESSAGES"
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    recipient: Mapped[int] = mapped_column(ForeignKey("USERS.id"))
    time_posted: Mapped[Datetime]
    title: Mapped[str]
    text: Mapped[str]

#See bookings by querying BOOKED, delete any availability of any type
class Availability(BaseTable):
    __tablename__ = "AVAILABILITIES"
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    buisness: Mapped[int] = mapped_column(ForeignKey("USERS.id"))

    available: Mapped[bool] = mapped_column(default=True) #False for blocked
    start_datetime: Mapped[Datetime] = mapped_column(DateTime(timezone=True))
    end_datetime: Mapped[Datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.max.replace(tzinfo=ZoneInfo("UTC")))
    days_supported: Mapped[int] = mapped_column(default=2**7-1) #Bitstring of 7 bits
    start_time: Mapped[Time]
    end_time: Mapped[Time]
    repetition: Mapped[str] = mapped_column(default="ONETIME")
    
    
    @hybrid_method
    def date_within_start_and_end(self, datetime): #For all datetime objects, it must be converted to UTC before passing into this function (this will be done when storing)
        return (self.start_datetime <= datetime) & (self.end_datetime >= datetime)
    
    @hybrid_method
    def time_within_start_and_end(self, datetime): #We assume that start_time and end_time
        return (self.start_time <= datetime.time()) & (self.end_time >= datetime.time())
        
    @hybrid_method
    def day_of_week_is_supported(self, datetime):
        return self.days_supported & (1 << datetime.weekday())
    
    @day_of_week_is_supported.expression
    def day_of_week_is_supported(self, datetime):
        return self.days_supported.bitwise_and(1 << datetime.weekday())
    
    @hybrid_method
    def in_the_same_week(self, datetime):
        return -(self.start_datetime.replace(month=datetime.month, year=datetime.year).timestamp()-datetime.timestamp()) <= 7*24*60*60
    
    @hybrid_method
    def on_the_right_day(self, datetime):
        if self.repetition=="DAILY":
            return True
        else:
            on_supported_weekday=self.day_of_week_is_supported(datetime)
            in_the_same_week=self.in_the_same_week(datetime)
 
            if self.repetition=="WEEKLY":
                return on_supported_weekday
            elif self.repetition=="MONTHLY":
                return on_supported_weekday & in_the_same_week 
            elif self.repetition=="YEARLY":
                return on_supported_weekday & in_the_same_week & (self.start_datetime.month==datetime.month)
            elif self.repetition=="ONETIME":
                return (self.start_datetime.year==datetime.year) and (self.start_datetime.month==datetime.month) and (self.start_datetime.day==datetime.day)
    
    @on_the_right_day.expression
    def on_the_right_day(self, datetime):
        return case(
            (self.repetition=="DAILY", True),
            (self.repetition=="ONETIME", (extract("year",self.start_datetime)==datetime.year) & (extract("month",self.start_datetime)==datetime.month) & (extract("day",self.start_datetime)==datetime.day)),
            else_ = self.day_of_week_is_supported(datetime) &
            case(
                (self.repetition=="WEEKLY", True),
                else_ = self.in_the_same_week(datetime) &
                case(
                    (self.repetition=="MONTHLY", True),
                    (self.repetition=="YEARLY", (extract("month",self.start_datetime)==datetime.month))
                )
            )
        )
                
        
    @hybrid_method
    def time_period_contains(self, datetime):
        return self.date_within_start_and_end(datetime) & self.time_within_start_and_end(datetime) & self.on_the_right_day(datetime)
    
    def has_service_expression(self, service):
        services_clause= true()
        for key in service:
            services_clause &= (getattr(Service,key)==service[key]) #service is a dictionary with keys that match the columns in the Service table

        return (select(Service.id).join_from(Availability_to_Service, Service, Availability_to_Service.service==Service.id, isouter=True).where(Availability_to_Service.availability==self.id & services_clause)).exists()

    @hybrid_method
    def has_service(self, service):
        return session.scalars(self.has_service_expression(service)).first() # Will return True or False
    
    @has_service.expression
    def has_service(self, service):
        return self.has_service_expression(service)

class Booking(BaseTable):
    __tablename__ = "BOOKINGS"
    
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    author: Mapped[int]
    availability_to_service: Mapped[int] = mapped_column(ForeignKey("AVAILABILITY_TO_SERVICE.id"))
    start_datetime: Mapped[Datetime]
    end_datetime: Mapped[Datetime]
    code: Mapped[int] #Must be random
    timestamp: Mapped[Datetime]
    
    def buisness_expression(self):
        return select(Availability.buisness).join_from(Availability_to_Service, Availability, Availability_to_Service.availability==Availability.id).where(Availability_to_Service.id==self.availability_to_service).limit(1)

    @hybrid_property
    def buisness(self):
        return session.scalars(self.buisness_expression()).first()

    @buisness.expression
    def buisness(self):
        return self.buisness_expression().scalar_subquery()

    
    #Later, if efficiency becomes a concern, we can add a modified time_period_contains here as is_within. However, that takes time, so I don't care right now

class Service(BaseTable):
   __tablename__="SERVICES"
   id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
   price: Mapped[float]

   device: Mapped[str]=mapped_column(nullable=True)
   device_repair: Mapped[str]=mapped_column(nullable=True)

   vehicle: Mapped[str]=mapped_column(nullable=True)
   vehicle_service: Mapped[str]=mapped_column(nullable=True)

   @property
   def services_dict(self): #Return dict of properties of service, remove id
        result={}
        for col in inspect(Service).attrs:
            key=col.key
            if key=="id":
                continue
            else:
                result[key]=getattr(self,key)

        return result


class Availability_to_Service(BaseTable):
    __tablename__= "AVAILABILITY_TO_SERVICE"
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    availability: Mapped[int] = mapped_column(ForeignKey("AVAILABILITIES.id", ondelete="CASCADE"))
    service: Mapped[int] = mapped_column(ForeignKey("SERVICES.id", ondelete="CASCADE"))

class Balance(BaseTable):
    __tablename__="BALANCE"
    
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    balance: Mapped[float] = mapped_column(default=0)

class Upload(BaseTable):
    __tablename__="UPLOADS"
    
    id: Mapped[int]= mapped_column(primary_key=True,autoincrement=True)
    type: Mapped[str] #Filetype
