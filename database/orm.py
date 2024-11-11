import datetime
from typing import List

import pytz
from sqlalchemy import select, delete, update, text, and_
from sqlalchemy.orm import joinedload, selectinload

import settings
from database.database import async_engine, async_session_factory
from database.tables import Base
from database import schemas
from database import tables


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
                query = select(tables.User).join(tables.User.events).filter(tables.Event.active == True) # TODO
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
                # TODO: сортировка по имени пользователя
                # .order_by(tables.User.firstname)

            result = await session.execute(query)
            row = result.scalars().first()

            event = schemas.EventRel.model_validate(row, from_attributes=True)
            return event

    @staticmethod
    async def get_events(only_active: bool = True) -> List[schemas.Event]:
        """Получение всех tables.Event"""
        async with async_session_factory() as session:
            if only_active:
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
        start_date = datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")).date()
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
    async def get_events_for_date(date: datetime.date) -> list[schemas.EventRel]:
        """Получение событий в определенную дату"""
        date_before = datetime.datetime.combine(date, datetime.datetime.min.time())
        date_after = date_before + datetime.timedelta(days=1)

        async with async_session_factory() as session:
            query = select(tables.Event)\
                .filter(and_(tables.Event.date > date_before, tables.Event.date < date_after)) \
                .options(joinedload(tables.Event.users_registered))\
                .order_by(tables.Event.date.asc())

            result = await session.execute(query)
            rows = result.unique().scalars().all()

            events = [schemas.EventRel.model_validate(row, from_attributes=True) for row in rows]
            return events

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
    async def set_level_for_user(user_id: int, level: str):
        """Назначение уровня пользователю"""
        async with async_session_factory() as session:
            query = update(tables.User)\
                .where(tables.User.id == user_id)\
                .values(level=level)

            await session.execute(query)
            await session.flush()
            await session.commit()

    @staticmethod
    async def update_event_status(event_id: int):
        """Изменение статуса прошедшего события"""
        async with async_session_factory() as session:
            query = update(tables.Event)\
                .where(tables.Event.id == event_id)\
                .values(active=False)

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
    async def get_payments_with_events_and_users(user_tg_id: str) -> list[schemas.PaymentsEventsUsers]:
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



