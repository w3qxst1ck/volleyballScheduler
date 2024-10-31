from database.tables import BaseCustom

Base = BaseCustom()   # model base class

from .tables import User, Event, EventsUsers