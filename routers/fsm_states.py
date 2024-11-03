from aiogram.fsm.state import StatesGroup, State


class RegisterUserFSM(StatesGroup):
    name = State()