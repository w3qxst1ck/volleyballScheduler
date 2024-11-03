from typing import List

from sqlalchemy import select
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
    async def get_users() -> List[schemas.User]:
        """Получение списка tables.User"""
        async with async_session_factory() as session:
            query = select(tables.User)
            result = await session.execute(query)
            rows = result.scalars().all()

            users = [schemas.User.model_validate(row, from_attributes=True) for row in rows]
            return users

    @staticmethod
    async def get_users_with_events() -> List[schemas.UserRel]:
        """Получение tables.User с tables.Events"""
        async with async_session_factory() as session:
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
    async def get_events() -> List[schemas.Event]:
        """Получение всех tables.Event"""
        async with async_session_factory() as session:
            query = select(tables.Event)
            result = await session.execute(query)
            rows = result.scalars().all()

            events = [schemas.Event.model_validate(row, from_attributes=True) for row in rows]
            return events

    @staticmethod
    async def get_events_with_users() -> List[schemas.EventRel]:
        """Получение всех tables.Event со связанными tables.User"""
        async with async_session_factory() as session:
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



