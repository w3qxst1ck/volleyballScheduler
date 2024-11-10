from pydantic_settings import BaseSettings, SettingsConfigDict


LEVELS = {
    "beginner": "Новичок",
    "beginner-plus": "🏐 Новичок+",
    "lite": "🥉 Лайт",
    "lite-plus": "🥈 Лайт +",
    "lite-plus-plus": "🥇 Лайт ++",
    "medium": "🏅 Медиум",
    "hard": "🏆 Хард",
}


class Database(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: str

    @property
    def DATABASE_URL(self):
        # postgresql+asyncpg://postgres:postgres@localhost:5432/
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Settings(BaseSettings):
    bot_token: str
    admins: list
    main_admin: str
    levels: dict = LEVELS
    admin_phone: str
    db: Database = Database()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

