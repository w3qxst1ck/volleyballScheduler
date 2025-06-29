from datetime import datetime
from typing import Any

from aiogram import Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import schemas
from database.orm import AsyncOrm
from routers.middlewares import CheckPrivateMessageMiddleware, CheckIsAdminMiddleware, DatabaseMiddleware
from settings import settings
from routers.fsm_states import AddTournamentFSM
from routers import keyboards as kb
from routers import utils


router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.message.middleware.register(CheckIsAdminMiddleware(settings.admins))
router.callback_query.middleware.register(CheckIsAdminMiddleware(settings.admins))
router.message.middleware.register(DatabaseMiddleware())
router.callback_query.middleware.register(DatabaseMiddleware())


# ADD TOURNAMENT
@router.message(Command("add_tournament"))
async def add_tournament_start_handler(message: types.Message, state: FSMContext) -> None:
    """Начало FSM"""
    msg = await message.answer("Отправьте тип турнира (например турнир для новичков)", reply_markup=kb.cancel_keyboard().as_markup())

    await state.set_state(AddTournamentFSM.type)
    await state.update_data(prev_mess=msg)


@router.message(AddTournamentFSM.type)
async def add_tournament_get_type_handler(message: types.Message, state: FSMContext) -> None:
    """Запись type, запрос title"""
    type = message.text
    await state.update_data(type=type)

    # изменение прошлого сообщения
    data = await state.get_data()
    try:
        await data["prev_mess"].edit_text(data["prev_mess"].text)
    except TelegramBadRequest:
        pass

    await state.set_state(AddTournamentFSM.title)
    msg = await message.answer("Отправьте описание турнира, не указывая дату",
                               reply_markup=kb.cancel_keyboard().as_markup())
    await state.update_data(prev_mess=msg)


@router.message(AddTournamentFSM.title)
async def add_tournament_title_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение title, выбор date"""
    title = message.text
    await state.update_data(title=title)

    # изменение прошлого сообщения
    data = await state.get_data()
    try:
        await data["prev_mess"].edit_text(data["prev_mess"].text)
    except TelegramBadRequest:
        pass

    msg = await message.answer("Введите дату в формате <b>ДД.ММ.ГГГГ</b> (например 25.07.2025)",
                               reply_markup=kb.cancel_keyboard().as_markup())

    await state.set_state(AddTournamentFSM.date)
    await state.update_data(prev_mess=msg)


@router.message(AddTournamentFSM.date)
async def add_tournament_date_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение date, выбор time"""
    date = message.text
    data = await state.get_data()

    # изменение предыдущего сообщения
    try:
        await data["prev_mess"].edit_text(data["prev_mess"].text)
    except TelegramBadRequest:
        pass

    # если ввели неправильную дату
    if not utils.is_valid_date(date):
        msg = await message.answer("Указан неверный формат даты\n\n"
                                   "Необходимо указать дату в формате <b>ДД.ММ.ГГГГ</b> без букв "
                                   "\"д\", \"м\" и \"г\" (например 25.07.2025)\n"
                                   "Дата не может быть раньше сегодняшней",
                                   reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если дата правильная
    await state.update_data(date=date)

    msg = await message.answer("Введите время в формате <b>ММ:ЧЧ</b> (например 09:00)",
                               reply_markup=kb.cancel_keyboard().as_markup())

    await state.set_state(AddTournamentFSM.time)
    await state.update_data(prev_mess=msg)


@router.message(AddTournamentFSM.time)
async def add_tournament_date_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение time, выбор min_team_count"""
    time = message.text
    data = await state.get_data()

    # изменение предыдущего сообщения
    try:
        await data["prev_mess"].edit_text(data["prev_mess"].text)
    except TelegramBadRequest:
        pass

    # неправильное время
    if not utils.is_valid_time(time):
        msg = await message.answer("Указан неверный формат времени\n\n"
                                   "Необходимо указать время в формате <b>ЧЧ:ММ</b> без букв \"м\" и \"ч\" "
                                   "(например 09:00 или 13:00)",
                                   reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если время правильное
    await state.update_data(time=time)

    msg = await message.answer("Введите минимальное количество команд <b>цифрой</b>",
                               reply_markup=kb.cancel_keyboard().as_markup())

    await state.set_state(AddTournamentFSM.min_team_count)
    await state.update_data(prev_mess=msg)


@router.message(AddTournamentFSM.min_team_count)
async def add_tournament_min_team_count_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение min_team_count, выбор max_team_places"""
    min_team_count = message.text
    data = await state.get_data()

    # изменение предыдущего сообщения
    try:
        await data["prev_mess"].edit_text(data["prev_mess"].text)
    except TelegramBadRequest:
        pass

    # неправильное количество мест
    if not utils.is_valid_places(min_team_count):
        msg = await message.answer("Введено некорректное число\n\n"
                                   "Необходимо указать <b>число</b> без букв, знаков препинания и других символов "
                                   "(например 8, 16 или 24)", reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если количество мест правильное
    await state.update_data(min_team_count=int(min_team_count))

    await state.set_state(AddTournamentFSM.max_team_places)

    msg = await message.answer(
        "Введите <b>максимальное</b> количество команд",
        reply_markup=kb.cancel_keyboard().as_markup()
    )
    await state.update_data(prev_mess=msg)


@router.message(AddTournamentFSM.max_team_places)
async def add_tournament_max_team_places_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение max_team_places, выбор min_team_players"""
    max_team_places = message.text
    data = await state.get_data()

    # изменение предыдущего сообщения
    try:
        await data["prev_mess"].edit_text(data["prev_mess"].text)
    except TelegramBadRequest:
        pass

    # неправильное количество мест
    if not utils.is_valid_places(max_team_places):
        msg = await message.answer("Введено некорректное число\n\n"
                                   "Необходимо указать <b>число</b> без букв, знаков препинания и других символов "
                                   "(например 8, 16 или 24)", reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если количество мест правильное
    await state.update_data(max_team_places=int(max_team_places))

    await state.set_state(AddTournamentFSM.min_team_players)

    msg = await message.answer(
        "Введите <b>минимальное</b> необходимое количество участников в команде для участия в турнире",
        reply_markup=kb.cancel_keyboard().as_markup()
    )
    await state.update_data(prev_mess=msg)


@router.message(AddTournamentFSM.min_team_players)
async def add_tournament_min_team_players_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение min_team_players, выбор max_team_players"""
    min_team_players = message.text
    data = await state.get_data()

    # изменение предыдущего сообщения
    try:
        await data["prev_mess"].edit_text(data["prev_mess"].text)
    except TelegramBadRequest:
        pass

    # неправильное количество мест
    if not utils.is_valid_places(min_team_players):
        msg = await message.answer("Введено некорректное число\n\n"
                                   "Необходимо указать <b>число</b> без букв, знаков препинания и других символов "
                                   "(например 8, 16 или 24)", reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если количество мест правильное
    await state.update_data(min_team_players=int(min_team_players))

    await state.set_state(AddTournamentFSM.max_team_players)

    msg = await message.answer(
        "Введите <b>максимальное</b> количество участников в команде",
        reply_markup=kb.cancel_keyboard().as_markup()
    )
    await state.update_data(prev_mess=msg)


@router.message(AddTournamentFSM.max_team_players)
async def add_tournament_max_team_players_handler(message: types.Message, state: FSMContext) -> None:
    """Сохранение max_team_players, выбор level"""
    max_team_players = message.text
    data = await state.get_data()

    # изменение предыдущего сообщения
    try:
        await data["prev_mess"].edit_text(data["prev_mess"].text)
    except TelegramBadRequest:
        pass

    # неправильное количество мест
    if not utils.is_valid_places(max_team_players):
        msg = await message.answer("Введено некорректное число\n\n"
                                   "Необходимо указать <b>число</b> без букв, знаков препинания и других символов "
                                   "(например 8, 16 или 24)", reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # если количество мест правильное
    await state.update_data(max_team_players=int(max_team_players))

    await state.set_state(AddTournamentFSM.level)

    msg = await message.answer("Выберите уровень турнира",
                               reply_markup=kb.tournament_levels_keyboards().as_markup())
    await state.update_data(prev_mess=msg)


@router.callback_query(AddTournamentFSM.level, lambda callback: callback.data.split("_")[0] == "admin-add-tournament-level")
async def add_tournament_date_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Сохранение level, выбор price"""
    level = int(callback.data.split("_")[1])
    await state.update_data(level=level)
    await state.set_state(AddTournamentFSM.price)

    await callback.message.edit_text("Введите цифрой цену турнира", reply_markup=kb.cancel_keyboard().as_markup())


@router.message(AddTournamentFSM.price)
async def save_tournament_handler(message: types.Message, state: FSMContext, session: Any) -> None:
    """Сохранение price, создание Tournament"""
    price_str = message.text
    data = await state.get_data()

    # изменение предыдущего сообщения
    try:
        await data["prev_mess"].edit_text(data["prev_mess"].text)
    except TelegramBadRequest:
        pass

    # неправильная цена
    if not utils.is_valid_price(price_str):
        msg = await message.answer("Введена некорректная цена\n\n"
                                   "Необходимо указать <b>число</b> без букв, знаков препинания и других символов "
                                   "(например 500, 1000 ил 1500)", reply_markup=kb.cancel_keyboard().as_markup())
        await state.update_data(prev_mess=msg)
        return

    # правильная цена
    date_time_str = f"{data['date']} в {data['time']}"
    date_time = datetime.strptime(f"{data['date']} {data['time']}", "%d.%m.%Y %H:%M")
    tournament = schemas.TournamentAdd(
        type=data["type"],
        title=data["title"],
        date=date_time,
        max_team_places=data["max_team_places"],
        min_team_count=data["min_team_count"],
        min_team_players=data["min_team_players"],
        max_team_players=data["max_team_players"],
        active=True,
        level=data["level"],
        price=price_str
    )

    await AsyncOrm.create_tournament(tournament, session)

    await state.clear()
    await message.answer(f"Турнир <b>\"{tournament.title}\"</b> <b>{date_time_str}</b> успешно создан ✅")