from aiogram.fsm.state import StatesGroup, State


class RegisterUserFSM(StatesGroup):
    name = State()


class AddEventFSM(StatesGroup):
    type = State()
    title = State()
    date = State()
    time = State()
    places = State()
    level = State()
    price = State()