from pydantic_settings import BaseSettings, SettingsConfigDict


class Database(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Settings(BaseSettings):
    bot_token: str
    admins: list
    db: Database = Database()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

