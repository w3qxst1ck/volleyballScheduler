from aiogram.fsm.state import StatesGroup, State


class RegisterUserFSM(StatesGroup):
    name = State()


class AddEventFSM(StatesGroup):
    type = State()
    title = State()
    date = State()
    time = State()
    places = State()
    min_count = State()
    level = State()
    price = State()


class AddTournamentFSM(StatesGroup):
    title = State()
    date = State()
    time = State()
    min_team_count = State()
    max_team_places = State()
    min_team_players = State()
    max_team_players = State()
    level = State()
    price = State()


class UpdateUserFSM(StatesGroup):
    name = State()
