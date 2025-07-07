from typing import Any, List

from aiogram import Router, types, F, Bot
from aiogram.enums import ParseMode
from aiogram.filters import or_f
from aiogram.fsm.context import FSMContext

from database.schemas import TeamUsers, User, Tournament, TournamentTeams
from logger import logger
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

    msg = ms.tournament_card_for_user_message(tournament, main_teams, reserve_teams)

    await callback.message.edit_text(
        msg,
        disable_web_page_preview=True,
        reply_markup=kb.tournament_card_keyboard(
            tournament,
            user.id,
            f"events-date_{utils.convert_date(tournament.date)}",
            main_teams,
            reserve_teams
        ).as_markup()
    )


# REG NEW TEAM
@router.callback_query(or_f(F.data.split("_")[0] == "register-new-team", F.data.split("_")[0] == "register-reserve-team"))
async def register_new_team(callback: types.CallbackQuery, state: FSMContext, session: Any) -> None:
    """Регистрация новой команды"""
    tournament_id = int(callback.data.split("_")[1])
    user = await AsyncOrm.get_user_by_tg_id(str(callback.from_user.id))
    tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)

    # проверяем допустимый ли уровень для создания команды
    if user.level > tournament.level or user.level == 1:
        msg = f"❗ Вы не можете участвовать в турнире уровня {settings.tournament_points[tournament.level][0]}"
        await callback.message.edit_text(
            msg,
            reply_markup=kb.back_keyboard(f"user-tournament_{tournament_id}").as_markup()
        )
        return

    # начинаем state
    await state.set_state(RegNewTeamFSM.title)

    # помечаем если резерв
    if callback.data.split("_")[0] == "register-reserve-team":
        await state.update_data(reserve=True)
    else:
        await state.update_data(reserve=False)

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

    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)
    team_users: List[TeamUsers] = await AsyncOrm.get_teams_with_users(tournament_id, session)
    to_reserve = data["reserve"]

    # если мест для команды уже нет
    if tournament.max_team_count <= len(team_users) or to_reserve:
        msg = f"📝 Команда <b>\"{team_title}\"</b> зарегистрирована в резерв, так как количество команд на турнире уже максимальное."

    # если места еще есть
    else:
        msg = f"✅ Команда <b>\"{team_title}\"</b> успешно зарегистрирована!"

    # Создаем новую команду
    try:
        await AsyncOrm.create_new_team(
            tournament_id,
            team_title,
            user.id,
            to_reserve,
            session
        )
    except Exception as e:
        await message.answer(f"Ошибка при создании команды", reply_markup=error_keyboard.as_markup())
        await state.clear()
        return

    await state.clear()

    keyboard = kb.back_to_tournament(tournament_id)
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

    # Проверяем в этой ли команде пользователь
    user_already_in_team: bool = False
    if user.id in [reg_user.id for reg_user in team.users]:
        user_already_in_team = True

    # если он не состоит ни в какой команде, есть ли место и позволяют ли баллы
    over_points: bool = False
    over_players_count: bool = False
    wrong_level: bool = False
    if not user_already_in_team and not user_already_has_another_team:
        # проверяем позволяет ли количество баллов зайти в команду
        team_with_new_user = team.users + [user]
        team_points = calculate_team_points(team_with_new_user)
        if team_points > settings.tournament_points[tournament.level][1]:
            over_points = True

        # проверяем есть ли место в команде
        if len(team.users) + 1 > tournament.max_team_players:
            over_players_count = True

        # проверяем позволяет ли уровень игрока записаться
        if user.level == 1 or user.level > tournament.level:
            wrong_level = True

    message = ms.team_card(team, user_already_in_team, user_already_has_another_team, over_points, over_players_count,
                           wrong_level)
    keyboard = kb.team_card_keyboard(tournament_id, team_id, user_already_in_team, user_already_has_another_team,
                                     over_points, over_players_count, wrong_level)
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
    keyboard = kb.yes_no_accept_user_in_team_keyboard(team_id, user.id, tournament_id)

    await bot.send_message(team_leader.tg_id, msg_for_leader, reply_markup=keyboard.as_markup())

    keyboard = kb.back_to_tournament(tournament_id)
    await callback.message.edit_text("ℹ️ Запрос на вступление в команду отправлен капитану, дождитесь его подтверждения",
                                     reply_markup=keyboard.as_markup())


# ACCEPT USER IN TEAM FOR TEAM LEADER
@router.callback_query(or_f(F.data.split("_")[0] == "accept-user-in-team",
                            F.data.split("_")[0] == "refuse-user-in-team"))
async def accept_refuse_user_in_team(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Прием или отклонение заявки пользователя в команду"""
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

    # прием в команду
    if callback.data.split("_")[0] == "accept-user-in-team":
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
                msg_for_captain = "Не удалось добавить пользователя в команду\n" \
                                  "Возможно в команде уже нет мест или команда удалена с турнира"
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
async def delete_team_from_tournament(callback: types.CallbackQuery, session: Any, bot: Bot) -> None:
    """Удаление команды или пользователя с турнира"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])
    tg_id = str(callback.from_user.id)

    user = await AsyncOrm.get_user_by_tg_id(tg_id)
    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)

    keyboard = kb.back_keyboard(f"user-tournament_{tournament_id}")

    # Для капитана удаляем всю команду
    if callback.data.split("_")[0] == "c-del-team":
        try:
            await AsyncOrm.delete_team_from_tournament(team_id, tg_id, session)
            await callback.message.edit_text(f"✅ Команда \"{team.title}\" удалена с турнира!", reply_markup=keyboard.as_markup())

            # уведомление участников команды об удалении команды
            converted_date = convert_date_named_month(tournament.date)
            msg = f"ℹ️ Капитан команды <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> удалил команду " \
              f"<b>{team.title}</b> с турнира \"{tournament.title}\" {converted_date}"
            for u in team.users:
                # пропускаем капитана
                if u.id == team.team_leader_id:
                    continue

                try:
                    await bot.send_message(u.tg_id, msg)
                except Exception:
                    pass

            # берем команду из резерва если они есть (при удалении основной команды)
            if team.reserve is False:
                try:
                    # получаем команду
                    reserve_team: TeamUsers = await AsyncOrm.get_first_reserve_team(tournament_id, session)

                    # меняем reserve на False
                    if reserve_team:
                        await AsyncOrm.transfer_team_from_reserve(reserve_team.team_id, session)

                        # оповещение участников команды переведенной из резерва
                        converted_date = convert_date_named_month(tournament.date)
                        msg = f"ℹ️ Ваша команда <b>{reserve_team.title}</b> переведена в основные команды турнира \"{tournament.title}\" {converted_date} " \
                              f"в связи с появлением свободного места."

                        for u in reserve_team.users:
                            try:
                                await bot.send_message(u.tg_id, msg)
                            except Exception:
                                pass

                except Exception:
                    pass

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

            # уведомление капитана
            captain = await AsyncOrm.get_user_by_id(team.team_leader_id)
            converted_date = convert_date_named_month(tournament.date)
            msg = f"ℹ️ Пользователь <a href='tg://user?id={user.tg_id}'>{user.firstname} {user.lastname}</a> вышел из команды " \
                  f"<b>{team.title}</b> турнира \"{tournament.title}\" {converted_date}"
            try:
                await bot.send_message(captain.tg_id, msg)
            except Exception:
                pass

        except:
            await callback.message.edit_text("Ошибка при выходе из команды, попробуйте позже")
            return





