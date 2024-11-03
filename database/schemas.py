import datetime

from pydantic import BaseModel


class UserAdd(BaseModel):
    tg_id: str
    username: str
    firstname: str
    lastname: str
    level: str | None = None


class User(UserAdd):
    id: int


class EventAdd(BaseModel):
    type: str
    title: str
    date: datetime.datetime
    places: int


class Event(EventAdd):
    id: int


class UserRel(User):
    events: list["Event"]


class EventRel(Event):
    users_registered: list["User"]




