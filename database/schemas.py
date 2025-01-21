import datetime

from pydantic import BaseModel


class UserAdd(BaseModel):
    tg_id: str
    username: str
    firstname: str
    lastname: str
    level: int | None = None


class User(UserAdd):
    id: int


class EventAdd(BaseModel):
    type: str
    title: str
    date: datetime.datetime
    places: int
    min_user_count: int
    level: int
    price: int


class Event(EventAdd):
    id: int
    active: bool


class UserRel(User):
    events: list["Event"]


class EventRel(Event):
    users_registered: list["User"]


class Payment(BaseModel):
    id: int
    paid: bool
    paid_confirm: bool
    event_id: int
    user_id: int


class PaymentsEventsUsers(Payment):
    event: Event
    user: User


class Reserved(BaseModel):
    id: int
    date: datetime.datetime


class EventsReservedForUser(Reserved):
    # user: User
    event: Event


class UsersReservedForEvent(Reserved):
    user: User
    # event: Event




