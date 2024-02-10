from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from utils import users
from sqlalchemy import func, select, literal, ForeignKey
from sqlalchemy import not_, and_, or_, case
from sqlalchemy.types import String

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
    __tablename__

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