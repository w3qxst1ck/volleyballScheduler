from typing import Any, List

from aiogram import Router, types, F, Bot

from database.orm import AsyncOrm
from database.schemas import TeamUsers, Tournament, User
from routers.middlewares import CheckPrivateMessageMiddleware, CheckIsAdminMiddleware, DatabaseMiddleware
from routers.utils import convert_date, convert_time, convert_date_named_month
from settings import settings
from routers import messages as ms
from routers import keyboards as kb
from routers import utils


router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.message.middleware.register(CheckIsAdminMiddleware(settings.admins))
router.callback_query.middleware.register(CheckIsAdminMiddleware(settings.admins))
router.message.middleware.register(DatabaseMiddleware())
router.callback_query.middleware.register(DatabaseMiddleware())


# ADMIN TOURNAMENT CARD
@router.callback_query(F.data.split("_")[0] == "admin-tournament")
async def admin_tournament_card(callback: types.CallbackQuery, session: Any) -> None:
    """Карточка турнира для админа"""
    tournament_id = int(callback.data.split("_")[1])

    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    teams_users: list[TeamUsers] = await AsyncOrm.get_teams_with_users(tournament_id, session)

    # разбиение на основные и резервные команды
    main_teams = []
    reserve_teams = []
    for team in teams_users:
        if team.reserve:
            reserve_teams.append(team)
        else:
            main_teams.append(team)

    # сортируем основные команды
    main_teams = [team for team in sorted(main_teams, key=lambda x: x.title)]

    msg = ms.tournament_card_for_user_message(tournament, main_teams, reserve_teams, for_admin=True)
    keyboard = kb.tournament_card_admin_keyboard(main_teams, reserve_teams, tournament_id)

    await callback.message.edit_text(msg, reply_markup=keyboard.as_markup(), disable_web_page_preview=True)


# DELETE TOURNAMENT
@router.callback_query(F.data.split("_")[0] == "admin-t-delete")
async def admin_delete_tournament(callback: types.CallbackQuery, session: Any) -> None:
    """Подтверждение удаления турнира администратором"""
    tournament_id = int(callback.data.split("_")[1])
    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)

    date = utils.convert_date(tournament.date)
    time = utils.convert_time(tournament.date)
    await callback.message.edit_text(
        f"Вы действительно хотите удалить турнир <b>{tournament.type} \"{tournament.title}\"</b> {date} в {time}?",
        reply_markup=kb.admin_confirmation_delete_tournament_keyboard(tournament_id).as_markup())


@router.callback_query(F.data.split("_")[0] == "admin-t-delete-confirm")
async def admin_delete_tournament_confirmed(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Удаление турнира"""
    admin_tg_id = str(callback.from_user.id)
    tournament_id = int(callback.data.split("_")[1])
    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    teams: List[TeamUsers] = await AsyncOrm.get_teams_with_users(tournament_id, session)

    try:
        # удаляем турнир
        await AsyncOrm.delete_tournament(tournament_id, admin_tg_id, session)

        # ответ админу
        admin_msg = "Турнир удален ✅"
        keyboard = kb.back_to_admin_events()
        await callback.message.edit_text(admin_msg, reply_markup=keyboard.as_markup())

        # оповещаем пользователей
        date = convert_date(tournament.date)
        time = convert_time(tournament.date)
        user_msg = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
                   f"Турнир <b>\"{tournament.title}\"</b>, запланированное <b>{date}</b> в <b>{time}</b>, " \
                   f"<b>отменено администратором</b>\n\n" \
                   f"По вопросу возврата оплаты обращайтесь к администратору @{settings.main_admin_url}"

        for team in teams:
            for user in team.users:
                try:
                    await bot.send_message(user.tg_id, user_msg)
                except Exception:
                    pass
    # при ошибке
    except:
        keyboard = kb.back_to_admin_events()
        await callback.message.edit_text("Ошибка при удалении турнира", reply_markup=keyboard.as_markup())
        return


# DELETE TEAM FROM TOURNAMENT
@router.callback_query(F.data.split("_")[0] == "admin-delete-team")
async def admin_delete_team(callback: types.CallbackQuery, session: Any) -> None:
    """Подтверждение удаления команды с турнира"""
    tournament_id = int(callback.data.split("_")[1])
    team_id = int(callback.data.split("_")[2])

    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    team: TeamUsers = await AsyncOrm.get_team(team_id, session)

    msg = f"Удалить команду \"{team.title}\" с турнира {tournament.title}?"
    keyboard = kb.admin_confirmation_delete_team_keyboard(tournament_id, team_id)

    await callback.message.edit_text(msg, reply_markup=keyboard.as_markup())


@router.callback_query(F.data.split("_")[0] == "delete-team-confirmed")
async def admin_delete_team_confirmed(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Удаление команды с турнира"""
    admin_tg_id = str(callback.from_user.id)
    tournament_id = int(callback.data.split("_")[1])
    team_id = int(callback.data.split("_")[2])

    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)

    # удаление команды
    try:
        await AsyncOrm.delete_team_from_tournament(team_id, admin_tg_id, session)

        # ответ админу
        admin_msg = f"Команда \"{team.title}\" удалена с турнира {tournament.title} ✅"
        keyboard = kb.back_to_admin_events()
        await callback.message.edit_text(admin_msg, reply_markup=keyboard.as_markup())

        # оповещение участников команды
        date = convert_date(tournament.date)
        time = convert_time(tournament.date)
        user_msg = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
                   f"Администратор удалил вашу команду \"{team.title}\" с турнира <b>\"{date} {time} {tournament.title}\"</b>!\n\n" \
                   f"Для уточнения деталей вы можете связаться с администратором @{settings.main_admin_url}"

        for user in team.users:
            try:
                await bot.send_message(user.tg_id, user_msg)
            except Exception:
                pass

    except:
        keyboard = kb.back_to_admin_events()
        await callback.message.edit_text("Ошибка при удалении команды с турнира", reply_markup=keyboard.as_markup())
        return

    # добор команды из резерва
    try:
        # получаем команду
        reserve_team: TeamUsers = await AsyncOrm.get_first_reserve_team(tournament_id, session)

        # меняем reserve на False
        if reserve_team:
            await AsyncOrm.transfer_team_from_reserve(reserve_team.team_id, session)

            # оповещение участников команды переведенной из резерва
            converted_date = convert_date_named_month(tournament.date)
            msg = f"🔔 <b>Автоматическое уведомление</b>\n\n" \
                  f"Ваша команда <b>{reserve_team.title}</b> переведена в основные команды турнира <b>\"{tournament.title}\" {converted_date}</b> " \
                  f"в связи с появлением свободного места."

            for u in reserve_team.users:
                try:
                    await bot.send_message(u.tg_id, msg)
                except Exception:
                    pass

    except Exception:
        pass


# LEVELS TOURNAMENT CARD
@router.callback_query(F.data.split("_")[0] == "admin-t-levels")
async def set_level_choose_team(callback: types.CallbackQuery, session: Any) -> None:
    """Выбор команды для выставления уровня участнику"""
    tournament_id = int(callback.data.split("_")[1])

    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    teams_users: List[TeamUsers] = await AsyncOrm.get_teams_with_users(tournament_id, session)

    # разбиение на основные и резервные команды
    main_teams = []
    reserve_teams = []
    for team in teams_users:
        if team.reserve:
            reserve_teams.append(team)
        else:
            main_teams.append(team)

    # сортируем основные команды
    main_teams = [team for team in sorted(main_teams, key=lambda x: x.title)]

    msg = ms.tournament_card_for_user_message(tournament, main_teams, reserve_teams, for_levels=True)
    keyboard = kb.tournament_card_level_keyboard(main_teams, reserve_teams, tournament_id)

    await callback.message.edit_text(msg, reply_markup=keyboard.as_markup(), disable_web_page_preview=True)


@router.callback_query(F.data.split("_")[0] == "admin-t-level-team")
async def set_level_choose_player(callback: types.CallbackQuery, session: Any) -> None:
    """Выбор участника для выставления уровня"""
    tournament_id = int(callback.data.split("_")[1])
    team_id = int(callback.data.split("_")[2])

    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    sorted_users = sorted(team.users, key=lambda u: u.level)

    # карточка команды
    msg = f"<b>{team.title}</b>\n\n"
    for idx, user in enumerate(sorted_users, start=1):
        msg += f"<b>{idx}.</b> <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> {settings.levels[user.level]}"
        if user.id == team.team_leader_id:
            msg += " (капитан)"
        msg += "\n"
    msg += f"\nЧтобы выставить уровень участника, нажмите кнопку с соответствующим номером участника"

    keyboard = kb.choose_player_for_level(sorted_users, tournament_id, team_id)
    await callback.message.edit_text(msg, reply_markup=keyboard.as_markup())


@router.callback_query(F.data.split("_")[0] == "admin-t-level-user")
async def set_level_choose_level(callback: types.CallbackQuery) -> None:
    """Выбор уровня для участника"""
    tournament_id = int(callback.data.split("_")[1])
    team_id = int(callback.data.split("_")[2])
    user_id = int(callback.data.split("_")[3])

    user: User = await AsyncOrm.get_user_by_id(user_id)

    if user.level:
        msg = f"Сейчас <b>{user.firstname} {user.lastname}</b> имеет уровень <b>{settings.levels[user.level]}</b>\n\n"
    else:
        msg = f"Сейчас <b>{user.firstname} {user.lastname} не имеет уровня</b>\n\n"
    msg += "Выберите уровень, который хотите установить пользователю"

    keyboard = kb.t_levels_keyboards(tournament_id, team_id, user_id)

    await callback.message.edit_text(msg, reply_markup=keyboard.as_markup())


@router.callback_query(lambda callback: callback.data.split("_")[0] == "admin-add-t-level")
async def update_level(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Установка уровня"""
    tournament_id = int(callback.data.split("_")[1])
    user_id = int(callback.data.split("_")[2])
    level = int(callback.data.split("_")[3])

    tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    teams_users: List[TeamUsers] = await AsyncOrm.get_teams_with_users(tournament_id, session)
    user: User = await AsyncOrm.get_user_by_id(user_id)

    # обновляем уровень
    await AsyncOrm.set_level_for_user(user_id, level)

    # сообщение админу
    await callback.message.edit_text(f"Уровень пользователя <b>{user.firstname} {user.lastname}</b> обновлен на {settings.levels[level]}")

    # второе сообщение админу
    # разбиение на основные и резервные команды
    main_teams = []
    reserve_teams = []
    for team in teams_users:
        if team.reserve:
            reserve_teams.append(team)
        else:
            main_teams.append(team)

    # сортируем основные команды
    main_teams = [team for team in sorted(main_teams, key=lambda x: x.title)]

    msg = ms.tournament_card_for_user_message(tournament, main_teams, reserve_teams, for_levels=True)
    keyboard = kb.tournament_card_level_keyboard(main_teams, reserve_teams, tournament_id)
    await callback.message.answer(msg, reply_markup=keyboard.as_markup(), disable_web_page_preview=True)

    # сообщение пользователю
    user_msg = ms.notify_set_level_message(level)
    await bot.send_message(str(user.tg_id), user_msg)



