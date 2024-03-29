from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy import ForeignKey, case
from sqlalchemy.types import DateTime
from datetime import datetime as Datetime
from datetime import time as Time
import datetime
from zoneinfo import ZoneInfo

# declarative base class
class BaseTable(DeclarativeBase):
    pass

class User(BaseTable):
    __tablename__ = "USERS"

    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
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
    author: Mapped[int] = mapped_column(ForeignKey("USERS.id"))
    available: Mapped[bool] = mapped_column(default=True) #False for blocked
    start_datetime: Mapped[Datetime] = mapped_column(DateTime(timezone=True))
    end_datetime: Mapped[Datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.max.replace(tzinfo=ZoneInfo("UTC")))
    days_supported: Mapped[int] = mapped_column(default=2**7-1) #Bitstring of 7 bits
    start_time: Mapped[Time]
    end_time: Mapped[Time]
    repetition: Mapped[str] = mapped_column(default="ONETIME")
    services: Mapped[str] = mapped_column(default="") #A,B C,D
    
    
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
            (self.repetition=="ONETIME", (self.start_datetime.year==datetime.year) & (self.start_datetime.month==datetime.month) & (self.start_datetime.day==datetime.day)),
            else_ = self.day_of_week_is_supported(datetime) &
            case(
                (self.repetition=="WEEKLY", True),
                else_ = self.in_the_same_week(datetime) &
                case(
                    (self.repetition=="MONTHLY", True),
                    (self.repetition=="YEARLY", (self.start_datetime.month==datetime.month))
                )
            )
        )
                
        
    @hybrid_method
    def time_period_contains(self, datetime):
        return self.date_within_start_and_end(datetime) & self.time_within_start_and_end(datetime) & self.on_the_right_day(datetime)
    
    @hybrid_method
    def has_service(self, service):
        return f" {service} " in self.services
    
    @has_service.expression
    def has_service(self, service):
        return self.services.contains(f" {service} ")

class Booking(BaseTable):
    __tablename__ = "BOOKINGS"
    
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    author: Mapped[int] = mapped_column(ForeignKey("USERS.id"))
    buisness: Mapped[int] = mapped_column(ForeignKey("USERS.id"))
    services: Mapped[str]
    start_datetime: Mapped[Datetime]
    end_datetime: Mapped[Datetime]
    availability_parent_id: Mapped[int] = mapped_column(ForeignKey("AVAILABILITIES.id"))
    code: Mapped[int] #Must be random
    
    #Later, if efficiency becomes a concern, we can add a modified time_period_contains here as is_within. However, that takes time, so I don't care right now
    

class Upload(BaseTable):
    __tablename__="UPLOADS"
    
    id: Mapped[int]= mapped_column(primary_key=True,autoincrement=True)
    type: Mapped[str]