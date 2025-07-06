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
    level: Mapped[int] = mapped_column(nullable=True)
    gender: Mapped[str] = mapped_column(nullable=True, default=None)

    events: Mapped[list["Event"]] = relationship(
        back_populates="users_registered",
        secondary="events_users",
    )

    teams: Mapped[list["Team"]] = relationship(
        back_populates="users",
        secondary="teams_users"
    )

    payments: Mapped[list["PaymentsUserEvent"]] = relationship(
        back_populates="user",
    )

    reserved: Mapped[list["Reserved"]] = relationship(
        back_populates="user"
    )


class Event(Base):
    """Таблица для событий"""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str]
    title: Mapped[str] = mapped_column(index=True)
    date: Mapped[datetime.datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    places: Mapped[int]
    min_user_count: Mapped[int]
    active: Mapped[bool] = mapped_column(default=True)
    level: Mapped[int]
    price: Mapped[int]

    users_registered: Mapped[list["User"]] = relationship(
        back_populates="events",
        secondary="events_users",
    )

    payments: Mapped[list["PaymentsUserEvent"]] = relationship(
        back_populates="event",
    )

    reserved: Mapped[list["Reserved"]] = relationship(
        back_populates="event",
    )


class EventsUsers(Base):
    """Many-to-many relationship"""
    __tablename__ = "events_users"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True
    )


class PaymentsUserEvent(Base):
    """Записи пользователей на мероприятия"""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    paid: Mapped[bool] = mapped_column(default=False)   # True если пользователь нажал "Оплатил"
    paid_confirm: Mapped[bool] = mapped_column(default=False)   # True если админ подтвердил платеж

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    event: Mapped["Event"] = relationship(back_populates="payments")

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship(back_populates="payments")


class Reserved(Base):
    """Запасные пользователи для участия в обычных событиях"""

    __tablename__ = "reserved"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship(back_populates="reserved")

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    event: Mapped["Event"] = relationship(back_populates="reserved")


class Tournament(Base):
    """Таблица турниров"""
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str]
    title: Mapped[str] = mapped_column(index=True)
    date: Mapped[datetime.datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    max_team_count: Mapped[int]
    min_team_count: Mapped[int]
    min_team_players: Mapped[int]
    max_team_players: Mapped[int]
    active: Mapped[bool] = mapped_column(default=True)
    level: Mapped[int]
    price: Mapped[int]

    teams: Mapped[list["Team"]] = relationship(
        back_populates="tournament"
    )

    payments: Mapped[list["PaymentsTournament"]] = relationship(
        back_populates="tournament"
    )

    reserved: Mapped[list["ReservedTournaments"]] = relationship(
        back_populates="tournament"
    )


class Team(Base):
    """Таблица команд для турнира"""
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(index=True)
    team_leader_id: Mapped[int] = mapped_column(nullable=False)
    team_libero_id: Mapped[int] = mapped_column(nullable=True)

    users: Mapped[list["User"]] = relationship(
        back_populates="teams",
        secondary="teams_users",
    )

    payment: Mapped["PaymentsTournament"] = relationship(
        back_populates="team",
        uselist=False,
        cascade="all, delete-orphan"
    )

    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    tournament: Mapped["Tournament"] = relationship(back_populates="teams")

    reserved: Mapped[list["ReservedTournaments"]] = relationship(back_populates="team")


class TeamsUsers(Base):
    """Many to many relationship"""
    __tablename__ = "teams_users"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        primary_key=True
    )


class ReservedTournaments(Base):
    """Запасные пользователи для участия в турнирах"""

    __tablename__ = "reserved_tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))

    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    team: Mapped["Team"] = relationship(back_populates="reserved")

    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    tournament: Mapped["Tournament"] = relationship(back_populates="reserved")


class PaymentsTournament(Base):
    """Полаты пользователями турниров"""

    __tablename__ = "tournament_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    paid: Mapped[bool] = mapped_column(default=False)   # True если пользователь нажал "Оплатил"
    paid_confirm: Mapped[bool] = mapped_column(default=False)   # True если админ подтвердил платеж

    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    tournament: Mapped["Tournament"] = relationship(back_populates="payments")

    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    team: Mapped["Team"] = relationship(back_populates="payment")




