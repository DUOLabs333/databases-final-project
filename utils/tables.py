from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.ext.hybrid import hybrid_method
from utils import users, availabilities
from sqlalchemy import select, literal, ForeignKey
from sqlalchemy import not_, and_, or_, case
from sqlalchemy.types import String
from datetime import datetime as Datetime
from datetime import Time
import time

# declarative base class
class BaseTable(DeclarativeBase):
    pass

class User(BaseTable):
    __tablename__ = "USERS"

    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    creation_time: Mapped[int]
    profile: Mapped[str] = mapped_column(default="")
    location_long: Mapped[float] = mapped_column(default=0)
    location_lat: Mapped[float] = mapped_column(default=0)
        
                
class Message(BaseTable): #Holds administrative messages and notifications of people booking service
    __tablename__ = "MESSAGES"
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    recipient: Mapped[int] = mapped_column(ForeignKey("USERS.id"))
    time_posted: Mapped[int]
    title: Mapped[str]
    text: Mapped[str]
    
    @hybrid_property
    def is_trendy(self):
        return (self.views>10) & (self.likes>=3*self.dislikes) & (self.type=="POST") & (self.time_posted>time.time()-5*60*60)
    
    @hybrid_property
    def trendy_ranking(self):
        return self.views/(self.dislikes+1)
    
    
    @hybrid_method
    def is_viewable(self,user):
        if not user.hasType(user.SURFER):
            return False
        if self.type not in self.public_types:
            if ((self.author==user.id) or self.parent==user.inbox): #Either user's inbox or message in that inbox
                return True
            if (user.hasType(user.SUPER)) and (self.type in ["REPORT","DISPUTE"]):
                return True
            else:
                return False
        else:
            return True
    
    @is_viewable.expression
    def is_viewable(cls,user):
        return case(
            (not_(user.hasType(user.SURFER)), False),
            (cls.type.in_(cls.public_types), True),
            else_=
                case(
                (or_(cls.author==user.id,cls.parent==user.inbox),True),
                (and_(cls.type.in_(["POST","DISPUTE"]),user.hasType(user.SUPER)),True),
                else_=False
                )
           )

class Availabilities(BaseTable):
    __tablename__ = "AVAILABILITIES"
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    author: Mapped[int] = mapped_column(ForeignKey("USERS.id"))
    available: Mapped[bool] = mapped_column(default=True)
    start_datetime: Mapped[Datetime]
    end_datetime: Mapped[Datetime]
    days_supported: Mapped[int] = mapped_column(default=2**8-1) #Bitstring of 7 bits
    start_time: Mapped[Time]
    end_time: Mapped[Time]
    type: Mapped[str] = mapped_column(default=availabilities.ONETIME)
    
    @hybrid_method
    def date_within_start_and_end(self, datetime): #For all datetime objects, it must be converted to UTC before passing into this function (this will be done when storing)
        return (self.start_datetime <= datetime) & (self.end_datetime >= datetime)
    
    @hybrid_method
    def time_within_start_and_end(self, time): #We assume that start_time and end_time
        return (self.start_time <= time) & (self.end_time >= time)
        
    @hybrid_method
    def day_of_week_is_supported(self, datetime):
        return self.days_supported & (1 << datetime.weekday())
    
    @day_of_week_is_supported.expression
    def day_of_week_is_supported(self, datetime):
        return self.days_supported.bitwise_and(1 << datetime.weekday())
    
    @hybrid_method
    def in_the_same_week(self, datetime):
        #Implement by subtracting the two unix timestamps and see if it is less than 7 days in seconds (use timestamp()). Remember to reverse it as self must be first
        pass
    

#available or not.
class Balance(BaseTable):
    __tablename__="BALANCE"
    
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    balance: Mapped[float] = mapped_column(default=0)

class Upload(BaseTable):
    __tablename__="UPLOADS"
    
    id: Mapped[int]= mapped_column(primary_key=True,autoincrement=True)
    path: Mapped[str]
    type: Mapped[str]