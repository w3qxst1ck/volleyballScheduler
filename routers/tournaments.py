from typing import Any

from aiogram import Router, types, F, Bot
from aiogram.enums import ParseMode
from aiogram.filters import or_f
from aiogram.fsm.context import FSMContext

from database.schemas import TeamUsers, User, Tournament
from routers.middlewares import CheckPrivateMessageMiddleware, DatabaseMiddleware
from routers import keyboards as kb, messages as ms
from routers.fsm_states import RegNewTeamFSM
from database.orm import AsyncOrm
from routers import utils
from settings import settings

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.callback_query.middleware.register(CheckPrivateMessageMiddleware())
router.message.middleware.register(DatabaseMiddleware())
router.callback_query.middleware.register(DatabaseMiddleware())


# FOR TOURNAMENTS
@router.callback_query(lambda callback: callback.data.split("_")[0] == "user-tournament")
async def user_tournament_handler(callback: types.CallbackQuery, session: Any, state: FSMContext) -> None:
    """Вывод карточки турнира для пользователя"""
    try:
        await state.clear()
    except:
        pass

    tournament_id = int(callback.data.split("_")[1])
    user_tg_id = str(callback.from_user.id)

    user = await AsyncOrm.get_user_by_tg_id(user_tg_id)
    tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)

    # Проверка есть ли у игрока уровень, для участия в турнире
    if not user.level:
        keyboard = kb.back_keyboard(f"events-date_{utils.convert_date(tournament.date)}")
        await callback.message.edit_text("Вы не можете участвовать в турнире, пока у вас не определен уровень",
                                         reply_markup=keyboard.as_markup())
        return

    # Проверка на пол
    if not user.gender:
        keyboard = kb.back_and_choose_gender_keyboard(f"events-date_{utils.convert_date(tournament.date)}")
        await callback.message.edit_text("Вы не можете участвовать в турнире, пока у вас не указан пол.\n"
                                         "Укажите пол в разделе \"👤 Мой профиль\".",
                                         reply_markup=keyboard.as_markup())
        return

    teams_users: list[TeamUsers] = await AsyncOrm.get_teams_with_users(tournament_id, session)

    msg = ms.tournament_card_for_user_message(tournament, teams_users)

    await callback.message.edit_text(
        msg,
        disable_web_page_preview=True,
        reply_markup=kb.tournament_card_keyboard(
            tournament,
            user.id,
            f"events-date_{utils.convert_date(tournament.date)}",
            teams_users
        ).as_markup()
    )


# REG NEW TEAM
@router.callback_query(F.data.split("_")[0] == "register-new-team")
async def register_new_team(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Регистрация новой команды"""
    tournament_id = int(callback.data.split("_")[1])

    # начинаем state
    await state.set_state(RegNewTeamFSM.title)

    keyboard = kb.back_keyboard(f"user-tournament_{tournament_id}")
    message = "Введите название команды"

    prev_message = await callback.message.edit_text(message, reply_markup=keyboard.as_markup())

    await state.update_data(prev_message=prev_message)
    await state.update_data(tournament_id=tournament_id)


@router.message(RegNewTeamFSM.title)
async def get_team_title(message: types.Message, state: FSMContext, session: Any) -> None:
    """Получаем название команды"""
    data = await state.get_data()
    tournament_id = data["tournament_id"]

    # Удаляем предыдущее сообщение
    try:
        await data["prev_message"].delete()
    except:
        pass

    error_keyboard = kb.back_keyboard(f"user-tournament_{tournament_id}")

    # Проверяем название команды
    try:
        team_title = message.text
    except:
        await message.answer("Некорректное название команды, попробуйте еще раз",
                             reply_markup=error_keyboard.as_markup())
        return

    team_leader_id = str(message.from_user.id)
    user = await AsyncOrm.get_user_by_tg_id(team_leader_id)

    # Создаем новую команду
    try:
        await AsyncOrm.create_new_team(
            tournament_id,
            team_title,
            user.id,
            user.level,
            session
        )
    except Exception as e:
        await message.answer(f"Ошибка при создании команды", reply_markup=error_keyboard.as_markup())
        await state.clear()
        return

    await state.clear()
    keyboard = kb.back_to_tournament(tournament_id)
    msg = f"✅ Команда <b>\"{team_title}\"</b> успешно зарегистрирована!\nТекущий уровень команды <b>{user.level}</b>"
    await message.answer(msg, reply_markup=keyboard.as_markup())


# КАРТОЧКА КОМАНДЫ
@router.callback_query(F.data.split("_")[0] == "register-in-team")
async def team_card(callback: types.CallbackQuery, session: Any) -> None:
    """Запись в существующую команду"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])
    tg_id = str(callback.from_user.id)

    user = await AsyncOrm.get_user_by_tg_id(tg_id)
    team = await AsyncOrm.get_team(team_id, session)

    # Проверяем зарегистрирован ли пользователь в какую нибудь из команд
    # tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    tournament_teams: list[TeamUsers] = await AsyncOrm.get_teams_with_users(tournament_id, session)

    user_already_has_another_team: bool = False
    for reg_team in tournament_teams:
        # Пропускаем текущую команду
        if reg_team.team_id == team.team_id:
            continue
        if user.id in [reg_user.id for reg_user in reg_team.users]:
            user_already_has_another_team = True

    # Проверяем в этой ли команде пользователь
    user_already_in_team: bool = False
    if user.id in [reg_user.id for reg_user in team.users]:
        user_already_in_team = True

    message = ms.team_card(team, user_already_in_team, user_already_has_another_team)
    keyboard = kb.team_card_keyboard(tournament_id, team_id, user_already_in_team, user_already_has_another_team)
    await callback.message.edit_text(message, reply_markup=keyboard.as_markup())


# REG USER IN TEAM
@router.callback_query(F.data.split("_")[0] == "reg-user-in-team")
async def reg_user_in_team(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Регистрация пользователя в существующую команду"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])
    tg_id = str(callback.from_user.id)

    # TODO проверки на уровень и кол-во участников

    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    team_leader: User = await AsyncOrm.get_user_by_id(team.team_leader_id)
    user: User = await AsyncOrm.get_user_by_tg_id(tg_id)

    # Отправляем сообщение капитану команды
    msg_for_leader = ms.message_for_team_leader(user, team, tournament)
    keyboard = kb.yes_no_accept_user_in_team_keyboard(team_id, user.id)

    await bot.send_message(team_leader.tg_id, msg_for_leader, reply_markup=keyboard.as_markup())

    keyboard = kb.back_keyboard(f"register-in-team_{team_id}_{tournament_id}")
    await callback.message.edit_text("Запрос на вступление в команду отправлен капитану, дождитесь его подтверждения",
                                     reply_markup=keyboard.as_markup())


# ACCEPT USER IN TEAM FOR TEAM LEADER
@router.callback_query(or_f(F.data.split("_")[0] == "accept-user-in-team",
                            F.data.split("_")[0] == "refuse-user-in-team"))
async def accept_refuse_user_in_team(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Прием или отклонение заявки пользователя в команду"""
    team_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])

    user: User = await AsyncOrm.get_user_by_id(user_id)
    team: TeamUsers = await AsyncOrm.get_team(team_id, session)

    # прием в команду
    if callback.data.split("_")[0] == "accept-user-in-team":
        try:
            await AsyncOrm.add_user_in_team(team_id, user_id, session)
            msg_for_captain = f" ✅ <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                              f"(ур. {settings.levels[user.level]}) добавлен в команду <b>{team.title}</b>"
            msg_for_user = f"✅ Капитан команды добавил вас в команду \"{team.title}\""

        # при ошибке (поль-ль уже в команде, слишком много людей, команда удалена и тд.)
        except Exception as e:
            msg_for_captain = "Не удалось добавить пользователя в команду\n" \
                              "Возможно в команде уже нет мест или команда удалена с турнира"
            msg_for_user = f" ❌ Капитан команды не добавил вас в команду \"{team.title}\""

    # отклонение
    else:
        msg_for_captain = f" ❌ Запрос <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                          f"(ур. {settings.levels[user.level]}) в команду \"{team.title}\" <b>отклонен</b>"
        msg_for_user = f" ❌ Капитан команды не добавил вас в команду \"{team.title}\""

    # отвечаем капитану
    await callback.message.edit_text(msg_for_captain)
    # оповещаем пользователя
    await bot.send_message(user.tg_id, msg_for_user)


# LEAVE FROM TEAM
@router.callback_query(F.data.split("_")[0] == "leave-user-from-team")
async def leave_from_team(callback: types.CallbackQuery, session: Any) -> None:
    """Запрос подтверждения выхода из команды"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])
    tg_id = str(callback.from_user.id)

    user = await AsyncOrm.get_user_by_tg_id(tg_id)
    team: TeamUsers = await AsyncOrm.get_team(team_id, session)

    message = f"Вы действительно хотите выйти из состава команды <b>\"{team.title}\"</b>?"
    # Проверяем капитан ли этот пользователь
    if not team.team_leader_id == user.id:
        user_is_team_leader = False
    else:
        user_is_team_leader = True
        message += f"\n❗ Вся команда будет удалена с турнира, так как вы являетесь капитаном"

    keyboard = kb.yes_no_leave_team_keyboard(user_is_team_leader, team_id, tournament_id)

    await callback.message.edit_text(message, reply_markup=keyboard.as_markup())


@router.callback_query(or_f(F.data.split("_")[0] == "c-del-team", F.data.split("_")[0] == "del-team"))
async def delete_team_from_tournament(callback: types.CallbackQuery, session: Any) -> None:
    """Удаление команды или пользователя с турнира"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])
    tg_id = str(callback.from_user.id)

    user = await AsyncOrm.get_user_by_tg_id(tg_id)
    team: TeamUsers = await AsyncOrm.get_team(team_id, session)

    keyboard = kb.back_keyboard(f"user-tournament_{tournament_id}")

    # Для капитана удаляем всю команду
    if callback.data.split("_")[0] == "c-del-team":
        try:
            await AsyncOrm.delete_team_from_tournament(team_id, tg_id, session)
            await callback.message.edit_text(f"✅ Команда \"{team.title}\" удалена с турнира!", reply_markup=keyboard.as_markup())

        except:
            await callback.message.edit_text("Ошибка при удалении команды, попробуйте позже")
            return

    # Удаляем одного пользователя из команды
    else:
        try:
            await AsyncOrm.delete_user_from_team(team_id, user.id, session)
            await callback.message.edit_text(
                f"✅ Вы вышли из команды \"{team.title}\"!",
                reply_markup=keyboard.as_markup()
            )

        except:
            await callback.message.edit_text("Ошибка при выходе из команды, попробуйте позже")
            return








