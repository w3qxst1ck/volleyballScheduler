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

        # проверяем не будет ли перебора с очками при переназначении либеро
        future_users = team.users + [team_libero]
        over_points = True if utils.calculate_team_points(future_users) > tournament.level else False

        msg_for_leader = ms.message_for_team_leader_about_libero(user, team, tournament, already_have_libero,
                                                                     over_points, team_libero)

    else:
        over_points = False
        msg_for_leader = ms.message_for_team_leader_about_libero(user, team, tournament, already_have_libero, over_points)

    # Отправляем сообщение капитану команды
    keyboard = kb.yes_no_accept_user_in_team_keyboard(team_id, user.id, tournament_id, for_libero=True)
    await bot.send_message(team_leader.tg_id, msg_for_leader, reply_markup=keyboard.as_markup())

    keyboard = kb.back_to_tournament(tournament_id)
    await callback.message.edit_text("🔔 <b>Автоматическое уведомление</b>\n\n"
                                     "Запрос на вступление в команду в качестве <b>либеро</b> отправлен капитану, "
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
    if callback.data.split("_")[0] == "accept-user-in-team":
        # проверка на количество участников в команде
        if len(team.users) + 1 > tournament.max_team_players:
            msg_for_captain = f"❌ Не удалось добавить пользователя в команду \"{team.title}\", так как команда уже заполнена"
            msg_for_user = f" ❌ Капитан команды не добавил вас в команду, так как команда \"{team.title}\" уже заполнена"

        # если пользователь уже в другой команде
        elif user_already_has_another_team:
            msg_for_captain = f"❌ Не удалось добавить пользователя в команду \"{team.title}\", так как он уже состоит в другой команде на этом турнире"
            msg_for_user = f" ❌ Капитан команды не добавил вас в команду \"{team.title}\", так как вы уже состоите в другой команде на этом турнире"

        # Если либеро еще нет записываем в команду
        elif already_have_libero:
            try:
                await AsyncOrm.add_user_in_team(team_id, user_id, session)
                await AsyncOrm.update_team_libero(team_id, user_id, session)

                msg_for_captain = f" ✅ <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                                  f"({settings.levels[user.level]}) добавлен в команду <b>{team.title}</b> в качестве либеро"
                msg_for_user = f"✅ Капитан команды добавил вас в команду \"{team.title}\" в качестве либеро"

            # при ошибке (поль-ль уже в команде, слишком много людей, команда удалена и тд.)
            except Exception as e:
                msg_for_captain = "❌ Не удалось добавить пользователя в команду.\n" \
                                  "Возможно в команде уже нет мест, команда удалена с турнира или игрок уже в команде"
                msg_for_user = f" ❌ Капитан команды не добавил вас в команду \"{team.title}\""

        # Если либеро уже есть в команде, записываем в команду
        else:
            old_libero: User = await AsyncOrm.get_user_by_id(team.team_libero_id)
            over_points = True if utils.calculate_team_points(team.users + [old_libero]) > tournament.level else False

            # если в команде перебор по очкам
            if over_points:
                await AsyncOrm.delete_user_from_team(team_id, old_libero.id, session)
                await AsyncOrm.add_user_in_team(team_id, user_id, session)
                await AsyncOrm.update_team_libero(team_id, user_id, session)

                msg_for_captain = f" ✅ <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                                  f"({settings.levels[user.level]}) добавлен в команду <b>{team.title}</b> в качестве либеро\n" \
                                  f"❗Игрок <a href='tg://user?id={old_libero.tg_id}'>{old_libero.firstname} {old_libero.lastname}</a> ({settings.levels[old_libero.level]}) " \
                                  f"исключен из команды, так как суммарное количество баллов превысило допустимое для этого турнира"
                msg_for_user = f"✅ Капитан команды добавил вас в команду \"{team.title}\" в качестве либеро"

                # оповещаем старого либеро
                msg_for_old_libero = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
                                     f"Капитан команды \"{team.title}\" удалил вас из команды на турнире \"{tournament.type}\" {tournament.title}"
                await bot.send_message(old_libero.tg_id, msg_for_old_libero)

            # когда нет перебора по очкам
            else:
                try:
                    await AsyncOrm.add_user_in_team(team_id, user_id, session)
                    await AsyncOrm.update_team_libero(team_id, user_id, session)

                    msg_for_captain = f" ✅ <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                                      f"({settings.levels[user.level]}) добавлен в команду <b>{team.title}</b> в качестве либеро"
                    msg_for_user = f"✅ Капитан команды добавил вас в команду \"{team.title}\" в качестве либеро"

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
