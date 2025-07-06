import datetime

from pydantic import BaseModel


class UserAdd(BaseModel):
    tg_id: str
    username: str
    firstname: str
    lastname: str
    level: int | None = None
    gender: str | None = None


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


class ReservedEvent(Reserved):
    event: Event


class ReservedUser(Reserved):
    user: User


class TeamUsers(BaseModel):
    team_id: int
    title: str
    team_leader_id: int
    team_libero_id: int | None = None
    users: list[User]


class TournamentAdd(BaseModel):
    type: str
    title: str
    date: datetime.datetime
    max_team_count: int
    min_team_count: int
    min_team_players: int
    max_team_players: int
    active: bool
    level: int
    price: int


class Tournament(TournamentAdd):
    id: int


class TournamentTeams(Tournament):
    teams: list[TeamUsers]


