from pydantic_settings import BaseSettings, SettingsConfigDict


LEVELS = {
    1: "Новичок",
    2: "🏐 Новичок+",
    3: "🥉 Лайт",
    4: "🥈 Лайт+",
    5: "🥇 Лайт++",
    6: "🏅 Медиум",
    7: "🏆 Хард",
}

TOURNAMENT_POINTS = {
    4: ("🥉 Новичок+/Лайт", 16),
    5: ("🥈 Лайт/Лайт+", 22),
    6: ("🥇 Лайт+/Лайт++", 32),
}

# LEVEL:POINTS
USER_POINTS = {
    "male": {
        1: 1,
        2: 1,
        3: 3,
        4: 4,
        5: 6,
        6: 7,
        7: 8,
    },
    "female": {
        1: 1,
        2: 1,
        3: 1,
        4: 2,
        5: 2,
        6: 3,
        7: 4,
    }
}

WEEKDAYS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


class Database(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: str

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Settings(BaseSettings):
    bot_token: str
    admins: list
    main_admin_url: str
    main_admin_tg_id: str
    levels: dict = LEVELS
    weekdays: dict = WEEKDAYS
    tournament_points: dict = TOURNAMENT_POINTS
    user_points: dict = USER_POINTS
    expire_event_days: int = 14
    admin_phone: str
    support_contact: str
    address: str = "Санкт-Петербург, Институтский пер., 5Н"
    notify_about_payment_days: int = 5
    kick_team_without_pay_days: int = 4
    db: Database = Database()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

