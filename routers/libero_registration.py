from typing import Any, List

from aiogram import Router, types, F, Bot
from aiogram.filters import or_f
from aiogram.fsm.context import FSMContext

from database.schemas import TeamUsers, User, Tournament, TournamentPayment
from routers.middlewares import CheckPrivateMessageMiddleware, DatabaseMiddleware
from routers import keyboards as kb, messages as ms
from routers.fsm_states import RegNewTeamFSM
from database.orm import AsyncOrm
from routers import utils
from routers.utils import calculate_team_points, convert_date_named_month
from settings import settings

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.callback_query.middleware.register(CheckPrivateMessageMiddleware())
router.message.middleware.register(DatabaseMiddleware())
router.callback_query.middleware.register(DatabaseMiddleware())


# REG LIBERO IN TEAM
@router.callback_query(F.data.split("_")[0] == "reg-libero-in-team")
async def reg_libero_in_team(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Регистрация либеро в существующую команду"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])
    tg_id = str(callback.from_user.id)

    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    team_leader: User = await AsyncOrm.get_user_by_id(team.team_leader_id)
    user: User = await AsyncOrm.get_user_by_tg_id(tg_id)

    # проверяем есть ли уже либеро в команде
    already_have_libero: bool = True if team.team_libero_id else False

    # если есть либеро, получаем данные игрока
    if already_have_libero:
        team_libero: User = await AsyncOrm.get_user_by_id(team.team_libero_id)
        wrong_level: bool = True if team_libero.level > tournament.level else False

        # проверяем не будет ли перебора с очками при переназначении либеро
        future_users = team.users + [team_libero]
        over_points = True if utils.calculate_team_points(future_users) > settings.tournament_points[tournament.level][1] else False

        msg_for_leader = ms.message_for_team_leader_about_libero(user, team, tournament, already_have_libero,
                                                                     over_points, team_libero, wrong_level)

    else:
        over_points = False
        msg_for_leader = ms.message_for_team_leader_about_libero(user, team, tournament, already_have_libero, over_points)

    # Отправляем сообщение капитану команды
    keyboard = kb.yes_no_accept_user_in_team_keyboard(team_id, user.id, tournament_id, for_libero=True)
    await bot.send_message(team_leader.tg_id, msg_for_leader, reply_markup=keyboard.as_markup())

    keyboard = kb.back_to_tournament(tournament_id)
    await callback.message.edit_text("Запрос на вступление в команду в качестве <b>либеро</b> отправлен капитану, "
                                     "дождитесь его подтверждения",
                                     reply_markup=keyboard.as_markup())


# ACCEPT LIBERO IN TEAM FOR TEAM LEADER
@router.callback_query(or_f(F.data.split("_")[0] == "accept-libero-in-team",
                            F.data.split("_")[0] == "refuse-libero-in-team"))
async def accept_refuse_user_in_team(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Прием или отклонение заявки либеро в команду"""
    team_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])
    tournament_id = int(callback.data.split("_")[3])

    user: User = await AsyncOrm.get_user_by_id(user_id)
    team: TeamUsers = await AsyncOrm.get_team(team_id, session)

    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    tournament_teams: list[TeamUsers] = await AsyncOrm.get_teams_with_users(tournament_id, session)

    # Проверяем зарегистрирован ли пользователь в какую нибудь из команд
    user_already_has_another_team: bool = False
    for reg_team in tournament_teams:
        # Пропускаем текущую команду
        if reg_team.team_id == team.team_id:
            continue
        if user.id in [reg_user.id for reg_user in reg_team.users]:
            user_already_has_another_team = True

    # проверяем есть ли уже либеро в команде
    already_have_libero: bool = True if team.team_libero_id else False

    # прием в команду
    if callback.data.split("_")[0] == "accept-libero-in-team":
        # проверка на количество участников в команде
        if len(team.users) + 1 > tournament.max_team_players:
            msg_for_captain = f"❌ Не удалось добавить пользователя в команду \"{team.title}\", так как команда уже заполнена"
            msg_for_user = f" ❌ Капитан команды не добавил вас в команду, так как команда \"{team.title}\" уже заполнена"

        # если пользователь уже в другой команде
        elif user_already_has_another_team:
            msg_for_captain = f"❌ Не удалось добавить пользователя в команду \"{team.title}\", так как он уже состоит в другой команде на этом турнире"
            msg_for_user = f" ❌ Капитан команды не добавил вас в команду \"{team.title}\", так как вы уже состоите в другой команде на этом турнире"

        # Если либеро еще нет записываем в команду
        elif not already_have_libero:
            try:
                await AsyncOrm.add_user_in_team(team_id, user_id, session)
                await AsyncOrm.update_team_libero(team_id, user_id, session)

                msg_for_captain = f" ✅ <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                                  f"({settings.levels[user.level]}) добавлен в команду <b>{team.title}</b> в качестве либеро"
                msg_for_user = f"✅ Капитан команды добавил вас в команду \"{team.title}\" в качестве <b>либеро</b> " \
                               f"на турнир <b>{tournament.type}</b> {tournament.title}"

            # при ошибке (поль-ль уже в команде, слишком много людей, команда удалена и тд.)
            except Exception as e:
                msg_for_captain = "❌ Не удалось добавить пользователя в команду.\n" \
                                  "Возможно в команде уже нет мест, команда удалена с турнира или игрок уже в команде"
                msg_for_user = f" ❌ Капитан команды не добавил вас в команду \"{team.title}\""

        # Если либеро уже есть в команде, записываем в команду
        else:
            old_libero: User = await AsyncOrm.get_user_by_id(team.team_libero_id)
            over_points = True if utils.calculate_team_points(team.users + [old_libero]) > settings.tournament_points[tournament.level][1] else False

            # если в команде перебор по очкам или по уровню игрока
            if over_points or old_libero.level > tournament.level:
                await AsyncOrm.delete_user_from_team(team_id, old_libero.id, session)
                await AsyncOrm.add_user_in_team(team_id, user_id, session)
                await AsyncOrm.update_team_libero(team_id, user_id, session)

                # причина выброса из команды
                reason = ""
                if over_points:
                    reason = ", так как суммарное количество баллов превысило допустимое для этого турнира"
                if old_libero.level > tournament.level:
                    reason = ", так как уровень игрока превышает допустимый на турнире"

                msg_for_captain = f" ✅ <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                                  f"({settings.levels[user.level]}) добавлен в команду <b>{team.title}</b> в качестве либеро\n" \
                                  f"❗Игрок <a href='tg://user?id={old_libero.tg_id}'>{old_libero.firstname} {old_libero.lastname}</a> ({settings.levels[old_libero.level]}) " \
                                  f"исключен из команды{reason}"
                msg_for_user = f"✅ Капитан команды добавил вас в команду \"{team.title}\" в качестве <b>либеро</b>"

                # оповещаем старого либеро
                msg_for_old_libero = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
                                     f"Капитан команды \"{team.title}\" удалил вас из команды на турнире \"{tournament.type}\" {tournament.title}"
                try:
                    await bot.send_message(old_libero.tg_id, msg_for_old_libero)
                except Exception:
                    pass

            # когда нет перебора по очкам и по уровню
            else:
                try:
                    await AsyncOrm.add_user_in_team(team_id, user_id, session)
                    await AsyncOrm.update_team_libero(team_id, user_id, session)

                    msg_for_captain = f" ✅ <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                                      f"({settings.levels[user.level]}) добавлен в команду <b>{team.title}</b> в качестве либеро"
                    msg_for_user = f"✅ Капитан команды добавил вас в команду \"{team.title}\" в качестве <b>либеро</b>"

                # при ошибке (поль-ль уже в команде, слишком много людей, команда удалена и тд.)
                except Exception as e:
                    msg_for_captain = "❌ Не удалось добавить пользователя в команду.\n" \
                                      "Возможно в команде уже нет мест, команда удалена с турнира или игрок уже в команде"
                    msg_for_user = f" ❌ Капитан команды не добавил вас в команду \"{team.title}\""

    # отклонение
    else:
        msg_for_captain = f" ❌ Запрос <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                          f"({settings.levels[user.level]}) в команду \"{team.title}\" <b>отклонен</b>"
        msg_for_user = f" ❌ Капитан команды не добавил вас в команду \"{team.title}\""

    # отвечаем капитану
    await callback.message.edit_text(msg_for_captain)
    # оповещаем пользователя
    keyboard = kb.back_to_tournament(tournament_id)
    await bot.send_message(user.tg_id, msg_for_user, reply_markup=keyboard.as_markup())


# CHOOSE LIBERO BY CAPTAIN
@router.callback_query(F.data.split("_")[0] == "choose-libero")
async def choose_libero_list(callback: types.CallbackQuery, session: Any) -> None:
    """Выбор либеро из членов команды для капитана"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])

    team: TeamUsers = await AsyncOrm.get_team(team_id, session)

    msg = f"<b>{team.title}</b>\n\n"

    for idx, user in enumerate(team.users, start=1):
        msg += f"<b>{idx}.</b> <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> {settings.levels[user.level]}\n"

    msg += "\nС помощью клавиатуры ниже выберите либеро"

    keyboard = kb.choose_libero(team, tournament_id)

    await callback.message.edit_text(msg, reply_markup=keyboard.as_markup())


@router.callback_query(F.data.split("_")[0] == "choose-libero-user")
async def choose_libero_user(callback: types.CallbackQuery, session: Any) -> None:
    """Подтверждение выбора игрока как либеро"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])
    new_libero_id = int(callback.data.split("_")[3])

    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    new_libero = await AsyncOrm.get_user_by_id(new_libero_id)

    # проверяем есть ли уже либеро
    if team.team_libero_id:
        old_libero = await AsyncOrm.get_user_by_id(team.team_libero_id)
        already_have_libero = True
    else:
        already_have_libero = False

    msg = f"Вы уверены, что хотите сделать игрока {new_libero.firstname} {new_libero.lastname} ({settings.levels[new_libero.level]}) либеро команды?"

    if already_have_libero:
        msg += f"\n\n❗Игрок {old_libero.firstname} {old_libero.lastname} ({settings.levels[old_libero.level]}) " \
               f"уже является либеро команды. Если количество его баллов будет превышать допустимое турниром, игрок будет исключен из команды."

    keyboard = kb.choose_libero_accept(team_id, tournament_id, new_libero_id)
    await callback.message.edit_text(msg, reply_markup=keyboard.as_markup())


@router.callback_query(F.data.split("_")[0] == "choose-liber-accept")
async def choose_libero_accept(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Выбор либеро подтвержден"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])
    new_libero_id = int(callback.data.split("_")[3])

    new_libero = await AsyncOrm.get_user_by_id(new_libero_id)
    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    converted_date = convert_date_named_month(tournament.date)

    # проверка есть ли уже либеро
    if team.team_libero_id:
        old_libero = await AsyncOrm.get_user_by_id(team.team_libero_id)
        already_have_libero = True
    else:
        already_have_libero = False

    # смена либеро
    await AsyncOrm.update_team_libero(team_id, new_libero_id, session)

    # сообщение капитану
    captain_msg = f"Игрок {new_libero.firstname} {new_libero.lastname} ({settings.levels[new_libero.level]}) " \
                  f"выбран в качестве либеро в команду \"{team.title}\""
    await callback.message.edit_text(captain_msg, reply_markup=kb.back_to_tournament(tournament_id).as_markup())

    # уведомляем нового либеро
    new_libero_msg = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
                     f"Вы выбраны в качестве либеро команды \"{team.title}\" " \
                     f"на турнир <b>{tournament.type}</b> {tournament.title} {converted_date}"

    try:
        await bot.send_message(new_libero.tg_id, new_libero_msg)
    except Exception:
        pass

    # если прошлый либеро превышал по очкам
    if already_have_libero and old_libero.level > tournament.level:
        # убираем игрока из команды
        await AsyncOrm.delete_user_from_team(team_id, old_libero.id, session)

        # уведомляем старого либеро
        old_libero_msg = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
                         f"Вы исключены из команды \"{team.title}\" на турнир <b>{tournament.type}</b> {tournament.title} " \
                         f"{converted_date}, так как ваш уровень превышает допустимый на турнире"

        try:
            await bot.send_message(old_libero.tg_id, old_libero_msg)
        except Exception:
            pass





