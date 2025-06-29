import datetime
from typing import List, Any
from collections.abc import Mapping

import pytz
from sqlalchemy import select, delete, update, text, and_
from sqlalchemy.orm import joinedload, selectinload
import asyncpg

import settings
from database.schemas import Tournament, TournamentAdd, Team, TeamUsers, User, UserAdd
from logger import logger
from database.database import async_engine, async_session_factory
from database.tables import Base
from database import schemas
from database import tables

Mapping.register(asyncpg.Record)


class AsyncOrm:
    @staticmethod
    async def create_tables():
        """Создание таблиц"""
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    # USERS
    @staticmethod
    async def add_user(user_add: schemas.UserAdd):
        """Создание tables.User"""
        async with async_session_factory() as session:
            user = tables.User(**user_add.dict())
            session.add(user)
            # flush взаимодействует с БД, поэтому пишем await
            await session.flush()
            await session.commit()

    @staticmethod
    async def update_user(tg_id: str, firstname: str, lastname: str):
        """Обновить ФИО пользователя"""
        async with async_session_factory() as session:
            query = update(tables.User) \
                .where(tables.User.tg_id == tg_id) \
                .values(firstname=firstname, lastname=lastname)

            await session.execute(query)
            await session.flush()
            await session.commit()

    @staticmethod
    async def get_user_by_id(user_id: int) -> schemas.User:
        """Получение tables.User по id"""
        async with async_session_factory() as session:
            query = select(tables.User).where(tables.User.id == user_id)
            result = await session.execute(query)
            row = result.scalars().first()

            user = schemas.User.model_validate(row, from_attributes=True)
            return user

    @staticmethod
    async def get_user_by_tg_id(tg_id: str) -> schemas.User | None:
        """Получение tables.User по tg_id"""
        async with async_session_factory() as session:
            query = select(tables.User).where(tables.User.tg_id == tg_id)
            result = await session.execute(query)
            row = result.scalars().first()

            if row:
                user = schemas.User.model_validate(row, from_attributes=True)
                return user
            else:
                return

    @staticmethod
    async def get_users() -> List[schemas.User]:
        """Получение списка tables.User"""
        async with async_session_factory() as session:
            query = select(tables.User)
            result = await session.execute(query)
            rows = result.scalars().all()

            users = [schemas.User.model_validate(row, from_attributes=True) for row in rows]
            return users

    @staticmethod
    async def get_user_with_events(tg_id: str, only_active: bool = True) -> schemas.UserRel:
        """Получение событий с этим пользователем"""
        async with async_session_factory() as session:
            query = select(tables.User).where(tables.User.tg_id == tg_id)\
                .options(selectinload(tables.User.events))

            result = await session.execute(query)

            row = result.scalars().first()

            user = schemas.UserRel.model_validate(row, from_attributes=True)

            # убираем неактивные события
            if only_active:
                events = filter(lambda event: event.active is True, user.events)
                user.events = events

            # сортируем по дате в порядке возрастания
            events = sorted(user.events, key=lambda event: event.date)
            user.events = events
            return user

    @staticmethod
    async def get_users_with_events(only_active: bool) -> List[schemas.UserRel]:
        """Получение tables.User с tables.Events"""
        async with async_session_factory() as session:
            if only_active:
                query = select(tables.User).join(tables.User.events).filter(tables.Event.active == True) # TODO что за туду непонятно???
            else:
                query = select(tables.User).options(joinedload(tables.User.events))
            result = await session.execute(query)
            rows = result.unique().scalars().all()

            users = [schemas.UserRel.model_validate(row, from_attributes=True) for row in rows]
            return users

    # EVENTS
    @staticmethod
    async def add_event(event: schemas.EventAdd):
        """Создание tables.Event"""
        async with async_session_factory() as session:
            event = tables.Event(**event.dict())
            session.add(event)
            await session.flush()
            await session.commit()

    @staticmethod
    async def delete_event(event_id: int) -> None:
        """Удаление из таблицы events"""
        async with async_session_factory() as session:
            query = delete(tables.Event).where(tables.Event.id == event_id)

            await session.execute(query)
            await session.flush()
            await session.commit()

    @staticmethod
    async def get_event_by_id(event_id: int) -> schemas.Event:
        """Получение tables.User по id"""
        async with async_session_factory() as session:
            query = select(tables.Event).where(tables.Event.id == event_id)
            result = await session.execute(query)
            row = result.scalars().first()

            event = schemas.Event.model_validate(row, from_attributes=True)
            return event

    @staticmethod
    async def get_event_with_users(event_id: int) -> schemas.EventRel:
        """Событие с его пользователями"""
        async with async_session_factory() as session:
            query = select(tables.Event) \
                .where(tables.Event.id == event_id) \
                .options(joinedload(tables.Event.users_registered))

            result = await session.execute(query)
            row = result.scalars().first()

            event = schemas.EventRel.model_validate(row, from_attributes=True)
            return event

    @staticmethod
    async def get_events(only_active: bool = True, days_ahead: int = None) -> List[schemas.Event]:
        """Получение всех tables.Event"""
        async with async_session_factory() as session:
            if only_active:
                if days_ahead:
                    date_now = datetime.datetime.now(tz=pytz.timezone("Europe/Moscow"))
                    query = select(tables.Event)\
                        .where(and_(
                            tables.Event.active == True,
                            tables.Event.date.between(date_now.date(), (date_now + datetime.timedelta(days=days_ahead)).date())
                        ))\
                        .order_by(tables.Event.date.asc())
                else:
                    query = select(tables.Event).where(tables.Event.active == True).order_by(tables.Event.date.asc())
            else:
                query = select(tables.Event).order_by(tables.Event.date.asc())
            result = await session.execute(query)
            rows = result.scalars().all()

            events = [schemas.Event.model_validate(row, from_attributes=True) for row in rows]
            return events

    @staticmethod
    async def get_last_events() -> List[schemas.Event]:
        """Получение последних tables.Event за 3 дня"""
        start_date = (datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")) + datetime.timedelta(days=1)).date()
        end_date = (datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")) - datetime.timedelta(days=3)).date()

        async with async_session_factory() as session:
            query = select(tables.Event) \
                    .filter(tables.Event.date.between(end_date, start_date)) \
                    .order_by(tables.Event.date.asc())
            result = await session.execute(query)
            rows = result.scalars().all()

            events = [schemas.Event.model_validate(row, from_attributes=True) for row in rows]
            return events

    @staticmethod
    async def get_events_with_users(only_active: bool = True) -> List[schemas.EventRel]:
        """Получение всех tables.Event со связанными tables.User"""
        async with async_session_factory() as session:
            if only_active:
                query = select(tables.Event).where(tables.Event.active == True).options(joinedload(tables.Event.users_registered))
            else:
                query = select(tables.Event).options(joinedload(tables.Event.users_registered))
            result = await session.execute(query)
            rows = result.unique().scalars().all()

            events = [schemas.EventRel.model_validate(row, from_attributes=True) for row in rows]
            return events

    @staticmethod
    async def get_events_for_date(date: datetime.date, only_active: bool = False) -> list[schemas.EventRel]:
        """Получение событий в определенную дату"""
        date_before = datetime.datetime.combine(date, datetime.datetime.min.time())
        date_after = date_before + datetime.timedelta(days=1)

        async with async_session_factory() as session:
            if only_active:
                query = select(tables.Event) \
                    .filter(and_(
                    tables.Event.date > date_before, tables.Event.date < date_after,
                    tables.Event.active == True,
                )) \
                    .options(joinedload(tables.Event.users_registered)) \
                    .order_by(tables.Event.date.asc())
            else:
                query = select(tables.Event)\
                    .filter(and_(
                        tables.Event.date > date_before, tables.Event.date < date_after,
                        ))\
                    .options(joinedload(tables.Event.users_registered))\
                    .order_by(tables.Event.date.asc())

            result = await session.execute(query)
            rows = result.unique().scalars().all()

            events = [schemas.EventRel.model_validate(row, from_attributes=True) for row in rows]
            return events

    @staticmethod
    async def delete_old_events(expire_days: int = 14):
        """Удаление events которые были позднее expire_days"""
        expire_date = datetime.datetime.now() - datetime.timedelta(days=expire_days)

        async with async_session_factory() as session:
            query = delete(tables.Event).where(tables.Event.date < expire_date)

            await session.execute(query)
            await session.flush()
            await session.commit()

    # EVENTS_USERS
    @staticmethod
    async def add_user_to_event(event_id: int, user_id: int):
        """Добавление tables.User в tables.Event.users_registered"""
        async with async_session_factory() as session:
            event_user = tables.EventsUsers(
                event_id=event_id,
                user_id=user_id
            )
            session.add(event_user)
            await session.flush()
            await session.commit()

    @staticmethod
    async def delete_user_from_event(event_id: int, user_id: int):
        """Удаление tables.User в tables.Event.users_registered"""
        async with async_session_factory() as session:
            query = delete(tables.EventsUsers)\
                .where(
                    (tables.EventsUsers.user_id == user_id) &
                    (tables.EventsUsers.event_id == event_id)
            )

            await session.execute(query)
            await session.flush()
            await session.commit()

    @staticmethod
    async def set_level_for_user(user_id: int, level: int):
        """Назначение уровня пользователю"""
        async with async_session_factory() as session:
            query = update(tables.User)\
                .where(tables.User.id == user_id)\
                .values(level=level)

            await session.execute(query)
            await session.flush()
            await session.commit()

    @staticmethod
    async def update_event_status_to_false(event_id: int):
        """Изменение статуса прошедшего события"""
        async with async_session_factory() as session:
            query = update(tables.Event)\
                .where(tables.Event.id == event_id)\
                .values(active=False)

            await session.execute(query)
            await session.flush()
            await session.commit()

    # RESERVE
    @staticmethod
    async def add_user_to_reserve(event_id: int, user_id: int):
        """Добавление tables.User в tables.Event.reserved"""
        async with async_session_factory() as session:
            reserve = tables.Reserved(event_id=event_id, user_id=user_id)
            session.add(reserve)
            await session.flush()
            await session.commit()

    @staticmethod
    async def get_reserved_events_by_user_id(user_id: int) -> List[schemas.ReservedEvent]:
        """Получение зарезервированных пользователем событий"""
        async with async_session_factory() as session:
            query = select(tables.Reserved) \
                .where(tables.Reserved.user_id == user_id)\
                .options(selectinload(tables.Reserved.event))
                # .options(selectinload(tables.Reserved.user))\

            result = await session.execute(query)
            rows = result.unique().scalars().all()

            users_reserved = [schemas.ReservedEvent.model_validate(row, from_attributes=True) for row in rows]

            users_reserved_sorted_by_date = sorted(users_reserved, key=lambda reserve: reserve.date)
            return users_reserved_sorted_by_date

    @staticmethod
    async def get_reserved_users_by_event_id(event_id: int) -> List[schemas.ReservedUser]:
        """Получение зарезервированных пользователей на событие"""
        async with async_session_factory() as session:
            query = select(tables.Reserved) \
                .where(tables.Reserved.event_id == event_id) \
                .options(selectinload(tables.Reserved.user))
                # .options(selectinload(tables.Reserved.event))

            result = await session.execute(query)
            rows = result.unique().scalars().all()

            events_reserved = [schemas.ReservedUser.model_validate(row, from_attributes=True) for row in rows]

            events_reserved_sorted_by_date = sorted(events_reserved, key=lambda reserve: reserve.date)

            return events_reserved_sorted_by_date

    @staticmethod
    async def transfer_from_reserve_to_event(event_id: int, user_id: int):
        """Перевод пользователя из резерва в основу"""
        await AsyncOrm.add_user_to_event(event_id, user_id)
        await AsyncOrm.delete_from_reserve(event_id, user_id)

    @staticmethod
    async def delete_from_reserve(event_id: int, user_id: int):
        """Удаление пользователя из резерва"""
        async with async_session_factory() as session:
            query = delete(tables.Reserved) \
                .where(and_(
                tables.Reserved.event_id == event_id,
                tables.Reserved.user_id == user_id
            ))

            await session.execute(query)
            await session.flush()
            await session.commit()

    # PAYMENTS
    @staticmethod
    async def create_payments(user_id: int, event_id: int):
        """Создание записи с платежом от пользователя"""
        async with async_session_factory() as session:
            payment = tables.PaymentsUserEvent(
                event_id=event_id,
                user_id=user_id,
                paid=True
            )
            session.add(payment)

            await session.flush()
            await session.commit()

    @staticmethod
    async def get_payment_by_id(payment_id: int) -> schemas.Payment:
        """Получение оплаты по id"""
        async with async_session_factory() as session:
            query = select(tables.PaymentsUserEvent)\
                .where(tables.PaymentsUserEvent.id == payment_id)

            result = await session.execute(query)
            row = result.scalars().first()

            payment = schemas.Payment.model_validate(row, from_attributes=True)
            return payment

    @staticmethod
    async def get_payment_by_event_and_user(event_id: int, user_id: int) -> schemas.Payment | None:
        """Получение оплаты по event_id and user_id """
        async with async_session_factory() as session:
            query = select(tables.PaymentsUserEvent)\
                .where(and_(
                        tables.PaymentsUserEvent.event_id == event_id,
                        tables.PaymentsUserEvent.user_id == user_id,
                )
            )

            result = await session.execute(query)
            row = result.scalars().first()
            if row:
                payment = schemas.Payment.model_validate(row, from_attributes=True)
                return payment
            return

    @staticmethod
    async def get_user_payments_with_events_and_users(user_tg_id: str) -> list[schemas.PaymentsEventsUsers]:
        """Получение оплаты по id"""
        user = await AsyncOrm.get_user_by_tg_id(user_tg_id)

        async with async_session_factory() as session:
            query = select(tables.PaymentsUserEvent)\
                .filter(and_(tables.PaymentsUserEvent.user_id == user.id,))\
                .options(joinedload(tables.PaymentsUserEvent.event))\
                .options(joinedload(tables.PaymentsUserEvent.user))\

            result = await session.execute(query)
            rows = result.unique().scalars().all()

            payments = [schemas.PaymentsEventsUsers.model_validate(row, from_attributes=True) for row in rows]
            payments_sorted_by_date = sorted(payments, key=lambda payment: payment.event.date)

            return payments_sorted_by_date

    @staticmethod
    async def update_payment_status(event_id: int, user_id: int) -> None:
        """Изменение статуса оплаты после подтверждения оплаты"""
        async with async_session_factory() as session:
            query = update(tables.PaymentsUserEvent) \
                .filter(and_(
                        tables.PaymentsUserEvent.event_id == event_id,
                        tables.PaymentsUserEvent.user_id == user_id,
                        )
            )\
                .values(paid_confirm=True)

            await session.execute(query)
            await session.flush()
            await session.commit()

    @staticmethod
    async def delete_payment(event_id: int, user_id: int) -> None:
        """Удаление из таблицы payments"""
        async with async_session_factory() as session:
            query = delete(tables.PaymentsUserEvent)\
                .where(and_(
                            tables.PaymentsUserEvent.event_id == event_id,
                            tables.PaymentsUserEvent.user_id == user_id
                )
            )

            await session.execute(query)
            await session.flush()
            await session.commit()

    @staticmethod
    async def get_all_players_info() -> List[schemas.User]:
        """Получение всех участников"""
        async with async_session_factory() as session:
            query = select(tables.User).order_by(tables.User.firstname, tables.User.lastname)
            result = await session.execute(query)
            rows = result.scalars().all()

            users = [schemas.User.model_validate(row, from_attributes=True) for row in rows]
            return users

    @staticmethod
    async def create_tournament(tournament: TournamentAdd, session: Any) -> None:
        """Создание турнира"""
        try:
            tournament_id = await session.fetchval(
                """
                INSERT INTO tournaments (type, title, date, max_team_count, min_team_count, min_team_players, max_team_players, active, level, price)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
                """,
                tournament.type, tournament.title, tournament.date, tournament.max_team_count, tournament.min_team_count,
                tournament.min_team_players, tournament.max_team_players, tournament.active, tournament.level, tournament.price
            )
            logger.info(f"Добавлен турнир с id {tournament_id} {tournament.title} {tournament.date}")

        except Exception as e:
            logger.error(f"Ошибка при создании турнира: {e}")

    @staticmethod
    async def get_all_tournaments(days_ahead: int, session: Any, active: bool = True) -> list[Tournament]:
        """Получение всех чемпионатов в выбранную данную"""
        date_before = datetime.datetime.combine(datetime.datetime.now().date(), datetime.datetime.min.time())
        date_after = date_before + datetime.timedelta(days=days_ahead)

        try:
            # Только активные
            if active:
                rows = await session.fetch(
                    """
                    SELECT * FROM tournaments
                    WHERE active=true AND date > $1 AND date < $2
                    """,
                    date_before, date_after
                )
                tournaments: list[Tournament] = [
                    Tournament.model_validate(row) for row in rows
                ]

                return tournaments
            # Вместе с неактивными
            else:
                rows = await session.fetch(
                    """
                    SELECT * FROM tournaments
                    WHERE date > $1 AND date < $2
                    """,
                    date_before, date_after
                )
                tournaments: list[Tournament] = [
                    Tournament.model_validate(row) for row in rows
                ]

                return tournaments

        except Exception as e:
            logger.error(f"Ошибка при получении чемпионатов в период {date_before} - {date_after}: {e}")

    @staticmethod
    async def get_all_tournaments_for_date(date: datetime.date, session: Any, active: bool = True) -> list[Tournament]:
        """Получение всех чемпионатов в выбранную данную"""
        date_before = datetime.datetime.combine(date, datetime.datetime.min.time())
        date_after = date_before + datetime.timedelta(days=1)

        try:
            # Только активные
            if active:
                rows = await session.fetch(
                    """
                    SELECT * FROM tournaments
                    WHERE active=true AND date > $1 AND date < $2
                    """,
                    date_before, date_after
                )
                tournaments: list[Tournament] = [
                    Tournament.model_validate(row) for row in rows
                ]

                return tournaments
            # Вместе с неактивными
            else:
                rows = await session.fetch(
                    """
                    SELECT * FROM tournaments
                    WHERE date > $1 AND date < $2
                    """,
                    date_before, date_after
                )
                tournaments: list[Tournament] = [
                    Tournament.model_validate(row) for row in rows
                ]

                return tournaments

        except Exception as e:
            logger.error(f"Ошибка при получении чемпионатов в период {date_before} - {date_after}: {e}")

    @staticmethod
    async def get_tournament_by_id(tournament_id: int, session: Any) -> Tournament:
        """Получение всех чемпионата по id"""
        try:
            row = await session.fetchrow(
                """
                SELECT * FROM tournaments
                WHERE id=$1
                """,
                tournament_id
            )
            tournament: Tournament = Tournament.model_validate(row)

            return tournament

        except Exception as e:
            logger.error(f"Ошибка при получении чемпионата {tournament_id}: {e}")

    @staticmethod
    async def get_teams_with_users(tournament_id: int, session: Any) -> list[TeamUsers]:
        """Получение команд вместе с пользователями"""
        try:
            rows = await session.fetch(
                """
                SELECT t.id AS team_id, t.title AS title, t.level AS team_level, t.team_leader_id as team_leader_id, 
                u.id AS user_id, u.tg_id AS tg_id, u.username AS username, u.firstname AS firstname, 
                u.lastname AS lastname, u.level AS user_level 
                FROM teams AS t
                JOIN teams_users AS tu ON t.id = tu.team_id
                JOIN users AS u ON tu.user_id=u.id
                WHERE tournament_id = $1
                """,
                tournament_id
            )
            result = []

            # Разбиваем пользователей по командам
            teams_users = {}
            for row in rows:
                user = User(
                        id=row["user_id"],
                        tg_id=row["tg_id"],
                        username=row["username"],
                        firstname=row["firstname"],
                        lastname=row["lastname"],
                        level=row["user_level"]
                )
                if row["title"] in teams_users.keys():
                    teams_users[row["title"]].append(user)
                else:
                    teams_users[row["title"]] = [user]

            # Формируем модель TeamUsers
            used_teams = []
            for row in rows:
                if row["title"] in used_teams:
                    continue
                else:
                    result.append(TeamUsers(
                        team_id=row["team_id"],
                        title=row["title"],
                        team_level=row["team_level"],
                        team_leader_id=row["team_leader_id"],
                        users=teams_users[row["title"]]
                    ))
                    used_teams.append(row["title"])

            return result

        except Exception as e:
            logger.error(f"Ошибка при получении команд с игроками для чемпионата {tournament_id}: {e}")

    @staticmethod
    async def get_team(team_id: int, session: Any) -> TeamUsers:
        """Получает команду с пользователями и капитаном"""
        try:
            rows = await session.fetch(
                """
                SELECT t.id AS team_id, t.title AS title, t.level AS team_level, t.team_leader_id as team_leader_id, 
                u.id AS user_id, u.tg_id AS tg_id, u.username AS username, u.firstname AS firstname, 
                u.lastname AS lastname, u.level AS user_level 
                FROM teams AS t
                JOIN teams_users AS tu ON t.id = tu.team_id
                JOIN users AS u ON tu.user_id=u.id
                WHERE t.id = $1
                """,
                team_id
            )
            result = []

            # Разбиваем пользователей по командам
            teams_users = {}
            for row in rows:
                user = User(
                    id=row["user_id"],
                    tg_id=row["tg_id"],
                    username=row["username"],
                    firstname=row["firstname"],
                    lastname=row["lastname"],
                    level=row["user_level"]
                )
                if row["title"] in teams_users.keys():
                    teams_users[row["title"]].append(user)
                else:
                    teams_users[row["title"]] = [user]

            # Формируем модель TeamUsers
            used_teams = []
            for row in rows:
                if row["title"] in used_teams:
                    continue
                else:
                    result.append(TeamUsers(
                        team_id=row["team_id"],
                        title=row["title"],
                        team_level=row["team_level"],
                        team_leader_id=row["team_leader_id"],
                        users=teams_users[row["title"]]
                    ))
                    used_teams.append(row["title"])

            return result[0]

        except Exception as e:
            logger.error(f"Ошибка при получении команды с игроками {team_id}: {e}")