from typing import List

from sqlalchemy import select, delete, update
from sqlalchemy.orm import joinedload

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
    async def get_user_with_events(tg_id: str) -> schemas.UserRel:
        """Получение событий с этим пользователем"""
        async with async_session_factory() as session:
            query = select(tables.User).where(tables.User.tg_id == tg_id) \
                .options(joinedload(tables.User.events))

            # query = """SELECT e.id, e.type, e.title, e.date, e.places, e.active, users.id
            #             FROM events AS e
            #             JOIN events_users ON events_users.event_id = e.id
            #             JOIN users ON events_users.user_id = users.id
            #             WHERE e.active = true
            #             ORDER BY e.id;"""

            result = await session.execute(query)
            row = result.scalars().first()

            user = schemas.UserRel.model_validate(row, from_attributes=True)
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
        """Добавление tables.User в tables.Event.users_registered"""
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
    async def update_event_status(event_id: int):
        """Изменение статуса прошедшего события"""
        async with async_session_factory() as session:
            query = update(tables.Event)\
                .where(tables.Event.id == event_id)\
                .values(active=False)

            await session.execute(query)
            await session.flush()
            await session.commit()




