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

    # Если игрок уже в команде
    if user in team.users:
        new_player = False

    # Если это новый игрок
    else:
        new_player = True

    # если есть либеро, получаем данные игрока
    if already_have_libero:
        team_libero: User = await AsyncOrm.get_user_by_id(team.team_libero_id)
        msg_for_leader = ms.message_for_team_leader_about_libero(user, team, tournament, already_have_libero, new_player, team_libero)
    else:
        msg_for_leader = ms.message_for_team_leader_about_libero(user, team, tournament, already_have_libero, new_player)

    # Отправляем сообщение капитану команды
    keyboard = kb.yes_no_accept_user_in_team_keyboard(team_id, user.id, tournament_id, for_libero=True)
    await bot.send_message(team_leader.tg_id, msg_for_leader, reply_markup=keyboard.as_markup())

    keyboard = kb.back_to_tournament(tournament_id)
    if new_player:
        await callback.message.edit_text("🔔 <b>Автоматическое уведомление</b>\n\n"
                                         "Запрос на вступление в команду в качестве <b>либеро</b> отправлен капитану, "
                                         "дождитесь его подтверждения",
                                         reply_markup=keyboard.as_markup())
    else:
        await callback.message.edit_text("🔔 <b>Автоматическое уведомление</b>\n\n"
                                         "Запрос отправлен капитану, дождитесь его подтверждения",
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

    # Если игрок уже в команде
    if user in team.users:
        new_player = False
    # Если это новый игрок
    else:
        new_player = True

    # проверяем есть ли уже либеро в команде
    already_have_libero: bool = True if team.team_libero_id else False

    # прием в команду
    if callback.data.split("_")[0] == "accept-user-in-team":
        # Если это новый игрок и либеро еще нет
        if new_player and not already_have_libero:
            # проверка на количество участников в команде
            if len(team.users) + 1 > tournament.max_team_players:
                msg_for_captain = f"❌ Не удалось добавить пользователя в команду \"{team.title}\", так как команда уже заполнена"
                msg_for_user = f" ❌ Капитан команды не добавил вас в команду, так как команда \"{team.title}\" уже заполнена"

        # Если игрок уже в команде
        else:
            pass

        team_users = team.users + [user]
        team_points = calculate_team_points(team_users)

        # проверка на количество участников в команде
        if len(team.users) + 1 > tournament.max_team_players:
            msg_for_captain = f"❌ Не удалось добавить пользователя в команду \"{team.title}\", так как команда уже заполнена"
            msg_for_user = f" ❌ Капитан команды не добавил вас в команду, так как команда \"{team.title}\" уже заполнена"

        # проверка на допустимый уровень
        elif team_points > settings.tournament_points[tournament.level][1]:
            msg_for_captain = f"❌ Не удалось добавить пользователя в команду \"{team.title}\", так как количество баллов команды будет превышать допустимое"
            msg_for_user = f" ❌ Капитан команды не добавил вас в команду, так как количество баллов команды \"{team.title}\" будет превышать допустимое"

        # Проверяем зарегистрирован ли пользователь в какую нибудь из команд
        elif user_already_has_another_team:
            msg_for_captain = f"❌ Не удалось добавить пользователя в команду \"{team.title}\", так как он уже состоит в другой команде на этом турнире"
            msg_for_user = f" ❌ Капитан команды не добавил вас в команду \"{team.title}\", так как вы уже состоите в другой команде на этом турнире"

        # пробуем записать в команду
        else:
            try:
                await AsyncOrm.add_user_in_team(team_id, user_id, session)
                msg_for_captain = f" ✅ <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> " \
                                  f"({settings.levels[user.level]}) добавлен в команду <b>{team.title}</b>"
                msg_for_user = f"✅ Капитан команды добавил вас в команду \"{team.title}\""

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
