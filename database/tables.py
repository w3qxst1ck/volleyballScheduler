import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy import text, ForeignKey


class Base(DeclarativeBase):
    repr_cols_num = 3
    repr_cols = tuple()

    def __repr__(self):
        """Relationships не используются в repr(), т.к. могут вести к неожиданным подгрузкам"""
        cols = []
        for idx, col in enumerate(self.__table__.columns.keys()):
            if col in self.repr_cols or idx < self.repr_cols_num:
                cols.append(f"{col}={getattr(self, col)}")

        return f"<{self.__class__.__name__} {', '.join(cols)}>"


class User(Base):
    """Таблица для хранения пользователей"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[str] = mapped_column(index=True, unique=True)
    username: Mapped[str] = mapped_column(nullable=True)
    firstname: Mapped[str]
    lastname: Mapped[str]
    level: Mapped[str] = mapped_column(nullable=True)

    events: Mapped[list["Event"]] = relationship(
        back_populates="users_registered",
        secondary="events_users",
    )


class Event(Base):
    """Таблица для событий"""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str]
    title: Mapped[str] = mapped_column(index=True)
    date: Mapped[datetime.datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    places: Mapped[int]

    users_registered: Mapped[list["User"]] = relationship(
        back_populates="events",
        secondary="events_users",
    )


class EventsUsers(Base):
    """Many to many relationship"""
    __tablename__ = "events_users"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True
    )








